import sqlalchemy
from sqlalchemy_utils import *
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy import (
    and_,
    inspect,
    Integer,
    Boolean,
    String,
    ForeignKey,
    DateTime,
    UniqueConstraint
)
from flask import current_app
from marshmallow import fields as ma_fields
from marshmallow_sqlalchemy.fields import Nested
from marshmallow_sqlalchemy import SQLAlchemySchema, SQLAlchemyAutoSchema, auto_field

import sys
import requests
import json
import datetime
from math import ceil, floor
from datetime import datetime as dt
from requests.structures import CaseInsensitiveDict as LazyDict

from application import db
from application.models import Setting
from application.models import Task, TaskRun
from application.decorators import with_logging
from .remote import RemotePetition

from .geographies.choices.regions import REGIONS
from .geographies.choices.constituencies import CONSTITUENCIES
from .geographies.choices.countries import COUNTRIES

class Petition(db.Model):
    __tablename__ = "petition"

    STATE_CHOICES = [
        ('C', 'closed'),
        ('R', 'rejected'),
        ('O', 'open'),
    ]
    STATE_LOOKUP = LazyDict({v: k for k, v in dict(STATE_CHOICES).items()})

    id = db.Column(Integer, primary_key=True, autoincrement=False)
    state = db.Column(ChoiceType(STATE_CHOICES), nullable=False)
    archived = db.Column(Boolean, default=False, nullable=False)
    records = relationship(lambda: Record, lazy='dynamic', back_populates="petition", cascade="all,delete")
    action = db.Column(String(512), index=True, unique=True)
    url = db.Column(String(2048), index=True, unique=True)
    signatures = db.Column(Integer)
    background = db.Column(String)
    creator_name = db.Column(String)
    additional_details = db.Column(String)
    pt_created_at = db.Column(DateTime)
    pt_updated_at = db.Column(DateTime)    
    pt_rejected_at = db.Column(DateTime)
    pt_closed_at = db.Column(DateTime)
    moderation_threshold_reached_at = db.Column(DateTime)
    response_threshold_reached_at = db.Column(DateTime)
    debate_threshold_reached_at = db.Column(DateTime)
    government_response_at = db.Column(DateTime)
    scheduled_debate_date = db.Column(DateTime)
    debate_outcome_at = db.Column(DateTime)
    polled_at = db.Column(DateTime)
    geo_polled_at = db.Column(DateTime)
    db_created_at = db.Column(DateTime, default=sqlfunc.now())
    db_updated_at = db.Column(DateTime, default=sqlfunc.now(), onupdate=sqlfunc.now())
    initial_data = db.Column(JSONType)
    latest_data = db.Column(JSONType)
    trend_pos = db.Column(Integer, default=0)
    
    # handles requests for remote operations
    remote = RemotePetition

    # manual work around for broken choice validation in sqlalchemy utils
    # also allows case agnostic value/key of the state tuple to be used as an argument
    @validates('state')
    def validate_state_choice(self, key, state):
        try:
            state = Petition.STATE_LOOKUP[state]
        except KeyError:
            dict(Petition.STATE_CHOICES)[state]

        return state

    def __repr__(self):
        template = '<id: {}, signatures: {}, created_at: {}>'
        return template.format(self.id, self.signatures, self.db_created_at)

    def __str__(self):
        template = 'petiton id: {}, action: {}'
        return template.format(self.id, self.action)

    @classmethod
    def filter_sig_attr(cls, attributes):
        return { 
            key.replace('signatures_by_', ''): val
            for key, val in attributes.items() if key.startswith('signatures_by_')
        }
    
    @classmethod
    def str_or_datetime(cls, time):
        return datetime.datetime.strptime(time, "%d-%m-%YT%H:%M:%S") if isinstance(time, str) else time

    @classmethod
    def get_setting(cls, *args, **kwargs):
        return Setting.get(*args, **kwargs)

    # onboard multiple remote petitions from the result of a query
    @classmethod
    @with_logging()
    def populate(cls, logger, state="open", signatures_by=False, count=False, archived=False, **kwargs):
        query = cls.remote.query(state=state, count=count, archived=archived, logger=logger)
        logger.info("remote query completed, matching petitions found: {}.".format(len(query)))
        
        logger.info("filtering query result against existing petition IDs")
        # this should be refactored into a single id.in_ query 
        ids = [item['id'] for item in query if not cls.query.get(item['id'])]

        logger.info("filter complete, to be onboarded: {}".format(len(ids)))
        remotes = cls.remote.async_get(ids=ids, retries=3, logger=logger).get('success')

        logger.info("populating petitions table from from result of async get")
        petitions = [cls.onboard(remote=r, signatures_by=signatures_by, logger=logger) for r in remotes]
        logger.info("petitions onboarded succesffully: {}".format(len(petitions)))

        return petitions

    # onboard a remote petition by id
    @classmethod
    @with_logging()
    def onboard(cls, logger, id=None, remote=None, signatures_by=False, **kwargs):
        remote = remote or cls.remote.get(id=id, raise_404=True, logger=logger)

        attributes = remote.data['data']["attributes"]
        total_sigs = attributes['signature_count']
        params = cls.remote.deserialize(remote.data)
        petition = Petition(**params)
        
        if signatures_by:
            petition.geo_polled_at = remote.timestamp
        else:
            petition.polled_at = remote.timestamp
        
        db.session.add(petition)
        db.session.commit()

        record = Record.create(
            petition_id=petition.id,
            timestamp=remote.timestamp,
            sigs_by=cls.filter_sig_attr(attributes),
            total_sigs=total_sigs,
            build_sigs_by=signatures_by,
            logger=logger
        )

        logger.info("onboarding complete for petition ID: {}".format(petition.id))
        return petition

    # poll all petitions which match where param and kwargs opts
    # signatures_by = True for full geo records, signatures_by = False for basic total records
    # if commit = False, poll will return the filtered responses with attached petition objs
    @classmethod
    @with_logging()
    def poll(cls, logger, where="all", signatures_by=False, commit=True, **kwargs):
        valid_where_values = ["trending", "signatures", "all"]
        if not where in valid_where_values:
            raise ValueError("Invalid param: {'where': {}}. Valid values: {}".format(where, valid_where_values))
        
        base_query = cls.query.filter_by(state="O", archived=False)
        if kwargs.get("last_polled"):
            polled_attr = Petition.geo_polled_at if kwargs.get("geo") else Petition.polled_at
            base_query = base_query.filter(polled_attr < kwargs["last_polled"])
        if where == "trending":
            threshold = kwargs.get("threshold") or Petition.get_setting('trending_threshold', type=int)
            petitions = base_query.order_by(Petition.trend_pos.desc()).limit(threshold).all()
        elif where == "signatures":
            threshold = kwargs.get("threshold") or Petition.get_setting('signatures_threshold', type=int)
            if kwargs.get("lt"):
                petitions = base_query.filter(Petition.signatures < threshold).all()
            else:
                petitions = base_query.filter(Petition.signatures > threshold).all()
        elif where == "all":
            petitions = base_query.all()
        
        logger.info("Petitions returned from query: {}".format(len(petitions)))
        if any(petitions):
            responses = cls.remote.async_poll(logger=logger, petitions=petitions, retries=3)
        if commit:
            responses = responses.get('success')
            logger.info("beginning poll commit")
            records =  [r.petition.commit_poll(logger=logger, response=r, signatures_by=signatures_by) for r in responses]
            logger.info("completed poll commmit")
            return records
        else:
            logger.info("skipping commit and returning poll responses")
            return responses
    
    # get the closest record for every petition within the lt/gt/now bounds
    @classmethod
    def get_all_with_distinct_record_at(cls, gt, lt=0, now=dt.now()):
        lt = now - datetime.timedelta(minutes=lt)
        gt = now - datetime.timedelta(minutes=gt)

        query = Record.query.distinct(Record.petition_id)
        query = query.filter(Record.timestamp > gt)
        query = query.filter(and_(Record.timestamp < lt))
        query = query.from_self().order_by(Record.timestamp.desc())
        
        petitions = []
        for record in query.all():
            record.petition.distinct_record = record
            petitions.append(record.petition)
        
        return petitions

    # update the trending pos for all petitions
    # optional before arg is the time of closest poll to compare
    @classmethod
    @with_logging()
    def update_trending(cls, logger, task_name="poll_total_sigs_task", before={"minutes": 60}, ts_range=2.5, **kwargs):
        last_run = Task.get_last_run(name=task_name, before=before)
        if not last_run:
            logger.info("Could not find any '{}' runs found before: {}".format(task_name, before))
            return []

        compare_to = round((dt.now() - last_run.finished_at).total_seconds() / 60)
        if not math.ceil(compare_to / 60) not in range(1, 13):
            raise RuntimeError("Comparison interval must be in range '1 to 12 hours'")
        
        time_range = {"gt": (compare_to + ts_range), "lt": (compare_to - ts_range)}
        petitions = Petition.get_all_with_distinct_record_at(**time_range)
        not_found = Petition.query.filter(Petition.id.notin_([p.id for p in petitions])).all()

        def sort_func(response):
            petition = response.petition
            curr_count = response.data['data']['attributes']['signature_count']
            petition.growth = curr_count - petition.distinct_record.signatures
            return petition.growth

        logger.info("async polling {} petitions, in range: {}".format(len(petitions), time_range))
        responses = cls.remote.async_poll(logger=logger, petitions=petitions, retries=3)
        successful, failed = responses.get('success', []), responses.get('failed', [])

        logger.info("sorting successful responses and updating trend_pos for petitions")
        responses.sort(key=lambda r: sort_func(r))
        for index, resp in enumerate(successful):
            resp.petition.trend_pos = index + 1
        
        if any(not_found):
            logger.info("defaulting 'not_found' petition trend_pos to 0")
            for petition in not_found:
                resp.petition.trend_pos = 0
        
        if any(failed):
            logger.info("defaulting 'failed' petition trend_pos to 0")
            for response in failed:
                petition.trend_pos = 0

        logger.info("trending petitions positions updated, commiting result")
        db.session.commit()
        return [response.petition for response in successful]

    # poll the petition instance, optional record commit and record build type (signatures_by) 
    @with_logging()
    def poll_self(self, logger, signatures_by=True, commit=True, **kwargs):
        logger.info('fetching remote petition ID: {}'.format(self.id))

        response = Petition.remote.get(self.id, raise_404=True)
        if commit:
            return self.commit_poll(response=response, signatures_by=signatures_by)
        else:
            return response

    # build record from poll response, must specify record build type (signatures_by)
    @with_logging("DEBUG")
    def commit_poll(self, logger, response, signatures_by, **kwargs):
        attributes = response.data['data']['attributes']
        total_sigs = attributes['signature_count']             
        if signatures_by:
            self.geo_polled_at = response.timestamp
        else:
            self.polled_at = response.timestamp
        
        self.update_attrs(attributes)        
        self.set_archive_state(response.data['data']['type'])
        self.latest_data = attributes
        self.signatures = attributes['signature_count']
        
        record = Record.create(
            petition_id=self.id,
            timestamp=response.timestamp,
            sigs_by=Petition.filter_sig_attr(attributes),
            total_sigs=attributes['signature_count'],
            build_sigs_by=signatures_by,
            logger=logger
        )

        logger.debug("completed poll for petition ID: {}".format(self.id))
        db.session.commit()
        return record

    # update petition with new attributes
    def update_attrs(self, attributes):
        self.state = attributes['state']
        self.pt_updated_at = attributes['updated_at']
        self.pt_rejected_at = attributes['rejected_at']
        self.moderation_threshold_reached_at = attributes['moderation_threshold_reached_at'] 
        self.response_threshold_reached_at = attributes['response_threshold_reached_at']
        self.debate_threshold_reached_at = attributes['debate_threshold_reached_at']
        self.government_response_at = attributes['government_response_at']
        self.scheduled_debate_date = attributes['scheduled_debate_date']
        self.debate_outcome_at = attributes['debate_outcome_at']
        self.pt_closed_at = attributes['closed_at']

    # set petition archival state
    def set_archive_state(self, type):
        self.archived = True if (type == 'archived-petition') else False
        return self.archived

    def get_closest_record_to(self, to, geographic=True):
        to = Petition.str_or_datetime(to)
        query = self.records.filter_by(geographic=geographic)
        query = query.filter(Record.timestamp < to)
        return query.order_by(Record.timestamp.desc()).first()

    # need to call .all() on returned value
    def query_records_between(self, lt, gt, geographic=True):
        lt, gt = Petition.str_or_datetime(lt), Petition.str_or_datetime(gt)
        query = self.records.filter_by(geographic=geographic)
        query = query.filter(Record.timestamp > gt).filter(and_(Record.timestamp < lt))
        return query.order_by(Record.timestamp.desc())

    # since ex: {'hours': 12}, {'days': 7}, {'month': 1}
    # need to call .all() on returned value
    def query_records_since(self, since, now=None, geographic=True):
        now = Petition.str_or_datetime(now) if now else dt.now()
        ago = now - datetime.timedelta(**since)
        query = self.records.filter(Record.timestamp > ago)
        query = query.filter_by(geographic=geographic)
        return query.order_by(Record.timestamp.desc())

    def ordered_records(self, order="DESC", geographic=True):
        if order == "DESC":
            return self.records.order_by(Record.timestamp.desc())
        if order == "ASC":
            return self.records.order_by(Record.timestamp.asc())
        
        raise ValueError("Invalid order param, Must be 'DESC' or 'ASC'")
    
    def latest_record(self, geographic=True):
        return self.ordered_records().filter_by(geographic=geographic).first()


class Record(db.Model):
    __tablename__ = 'record'

    id = db.Column(Integer, primary_key=True)
    petition_id = db.Column(Integer, ForeignKey(Petition.id), index=True, nullable=False)
    petition = relationship(Petition, back_populates="records")
    by_country = relationship("SignaturesByCountry", back_populates="record", cascade="all,delete")
    by_region = relationship("SignaturesByRegion", back_populates="record", cascade="all,delete")
    by_constituency = relationship("SignaturesByConstituency", back_populates="record", cascade="all,delete")
    signatures_by_country = relationship("SignaturesByCountry", lazy='dynamic', back_populates="record", cascade="all,delete")
    signatures_by_region = relationship("SignaturesByRegion", lazy='dynamic', back_populates="record", cascade="all,delete")
    signatures_by_constituency = relationship("SignaturesByConstituency", lazy='dynamic', back_populates="record", cascade="all,delete")
    timestamp = db.Column(DateTime, index=True, nullable=False)
    db_created_at = db.Column(DateTime, default=sqlfunc.now(), nullable=False)
    signatures = db.Column(Integer, nullable=False)
    geographic = db.Column(Boolean, default=False)

    def __repr__(self):
        template = '<record_id: {}, petition_id: {}, timestamp: {}, signatures: {}>'
        return template.format(self.id, self.petition_id, self.timestamp, self.signatures)
    
    def __str__(self):
        template = 'Total signatures for petition ID: {}, at {}: {}'
        return template.format(self.petition_id, self.timestamp, self.signatures)
    
    @classmethod
    def get_sig_model(cls, geography):
        return getattr(sys.modules[__name__], ('SignaturesBy' + geography.capitalize()))   

    @classmethod
    def get_sig_model_table(cls, geography):
        model = cls.get_sig_model(geography)
        return model, model.__table__

    @classmethod
    def signature_model_attributes(cls, geographies):
        attributes = {}
        for geo in geographies:
            model, table = cls.get_sig_model_table(geo)
            attributes[geo] = {
                'model': model,
                'table': table,
                'name': model.__tablename__,
                'relationship': getattr(cls, model.__tablename__),
                'schema_class': SignaturesBySchema.get_schema_for(geo),
            }
        return attributes
    
    @classmethod
    def get_sig_choice(cls, geography, key_or_value):
        model = cls.get_sig_model(geography)
        choices = dict(model.CODE_CHOICES)

        try:
            choices[key_or_value.upper()]
            code = key_or_value.upper()
        except KeyError:
            code = model.CODE_LOOKUP[key_or_value]

        value = choices[code]
        return {'code': code, 'value': value}
    
    # create a new record for the petition
    @classmethod
    @with_logging("DEBUG")
    def create(cls, logger, petition_id, timestamp, sigs_by, total_sigs, build_sigs_by, **kwargs):
        record = Record(
            timestamp=timestamp,
            signatures=total_sigs,
            petition_id=petition_id,
            geographic=build_sigs_by
        )

        db.session.add(record)
        db.session.commit()

        if record.geographic and any(sigs_by.values()):
            created = []
            for geo in list(sigs_by.keys()):
                model = cls.get_sig_model(geo)
                code = 'code' if geo == 'country' else 'ons_code'
                for locale in sigs_by[geo]:
                    created.append(model(record_id=record.id, code=locale[code], count=locale["signature_count"]))

            db.session.bulk_save_objects(created)
            logger.debug("signatures_by record created for petition ID: {}".format(petition_id))
        else:
            logger.debug("total_signatures record created for petition ID: {}".format(petition_id))

        db.session.commit()
        return record
    
    # short hand query helper query for signature geography + code or name
    def signatures_by(self, geography, locale):
        model = Record.get_sig_model(geography)
        relation = self.get_sig_relation(geography)
        choice = Record.get_sig_choice(geography, locale)

        try: 
            return relation.filter(model.code == choice['code']).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return None

    def get_sig_relation(self, geography):
        return getattr(self, 'signatures_by_' + geography)
    
    def signatures_comparison(self, schema, attrs):
        comparison = schema.dump(self)
        for geo in attrs.keys():
            relation = self.get_sig_relation(geo)
            filtered = relation.filter(attrs[geo]['model'].code.in_(attrs[geo]['locales'])).all()
            comparison[attrs[geo]['name']] = [attrs[geo]['schema'].dump(sig) for sig in filtered]
        return comparison



class SignaturesByCountry(db.Model):
    __tablename__ = 'signatures_by_country'
    __table_args__ = (
        db.UniqueConstraint('record_id', 'iso_code', name="uniq_sig_country_for_record"),
    )
    CODE_CHOICES = COUNTRIES
    CODE_LOOKUP = LazyDict({v: k for k, v in dict(CODE_CHOICES).items()})
    code = synonym("iso_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id), index=True, nullable=False)
    record = relationship(Record, back_populates="signatures_by_country")
    iso_code = db.Column(ChoiceType(CODE_CHOICES), index=True, nullable=False)
    count = db.Column(Integer, default=0)

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates('iso_code')
    def validate_code_choice(self, key, value):
        return ModelUtils.validate_geography_choice(self, key, value)
    
    def __str__(self):
        return '{} - {}'.format(self.code.value, self.count)



class SignaturesByRegion(db.Model):
    __tablename__ = 'signatures_by_region'
    __table_args__ = (
        db.UniqueConstraint('record_id', 'ons_code', name="uniq_sig_region_for_record"),
    )
    CODE_CHOICES = REGIONS
    CODE_LOOKUP = LazyDict({v: k for k, v in dict(CODE_CHOICES).items()})
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id), index=True, nullable=False)
    record = relationship(Record, back_populates="signatures_by_region")
    ons_code = db.Column(ChoiceType(CODE_CHOICES), index=True, nullable=False)
    count = db.Column(Integer, default=0)

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates('ons_code')
    def validate_code_choice(self, key, value):
        return ModelUtils.validate_geography_choice(self, key, value)
    
    def __str__(self):
        return '{} - {}'.format(self.code.value, self.count)



class SignaturesByConstituency(db.Model):
    __tablename__ = 'signatures_by_constituency'
    __table_args__ = (
        db.UniqueConstraint('record_id', 'ons_code', name="uniq_sig_constituency_for_record"),
    )
    CODE_CHOICES = CONSTITUENCIES
    CODE_LOOKUP = LazyDict({v: k for k, v in dict(CODE_CHOICES).items()})
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id), index=True, nullable=False)
    record = relationship(Record, back_populates="signatures_by_constituency")
    ons_code = db.Column(ChoiceType(CODE_CHOICES), index=True,  nullable=False)
    count = db.Column(Integer, default=0)

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates('ons_code')
    def validate_code_choice(self, key, value):
        return ModelUtils.validate_geography_choice(self, key, value)
    
    def __str__(self):
        return '{} - {}'.format(self.code.value, self.count)



# model deserialisation schemas
class SignaturesBySchema(SQLAlchemyAutoSchema):
    class Meta:
        include_relationships = True
        exclude = ["id"]

    @classmethod
    def get_schema_for(cls, geography):
        return getattr(
            sys.modules[__name__],
            "SignaturesBy{}{}".format(geography.capitalize(), 'Schema')
        )

    def format_timestamp(self, obj):
        return obj.timestamp.strftime("%d-%m-%YT%H:%M:%S")

    def get_code_field(self, obj):
        return obj.code.code

    def get_name_field(self, obj):
        return obj.code.value

    timestamp = ma_fields.Method("format_timestamp")
    code = ma_fields.Method("get_code_field")
    name = ma_fields.Method("get_name_field")

class SignaturesByConstituencySchema(SignaturesBySchema):
    class Meta(SignaturesBySchema.Meta):
        model = SignaturesByConstituency
        exclude = ["record", "id", "ons_code"]
    constituency = auto_field("ons_code", dump_only=True)

class SignaturesByCountrySchema(SignaturesBySchema):
    class Meta(SignaturesBySchema.Meta):
        model = SignaturesByCountry
        exclude = ["record", "id", "iso_code"]
    country = auto_field("iso_code", dump_only=True)

class SignaturesByRegionSchema(SignaturesBySchema):
    class Meta(SignaturesBySchema.Meta):
        model = SignaturesByRegion
        exclude = ["record", "id", "ons_code"]
    region = auto_field("ons_code", dump_only=True)



class RecordSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Record
        exclude = ["db_created_at", "geographic", "signatures", "by_country", "by_region", "by_constituency"]
    
    def format_timestamp(self, obj):
        return obj.timestamp.strftime("%d-%m-%YT%H:%M:%S")

    def rename_sig_key(self, obj):
        return obj.signatures

    total = ma_fields.Method("rename_sig_key")
    timestamp = ma_fields.Method("format_timestamp")

class RecordNestedSchema(RecordSchema):
    class Meta(RecordSchema.Meta):
        include_relationships = True
    
    relations = {
        "signatures_by_country",
        "signatures_by_region",
        "signatures_by_constituency"
    }

    @classmethod
    def get_exclusions_for(cls, *include):
        include = {"signatures_by_{}".format(i) for i in include}
        return (cls.relations.difference(include))

    total = ma_fields.Method("rename_sig_key")
    signatures_by_country = Nested(SignaturesByCountrySchema, many=True)
    signatures_by_region = Nested(SignaturesByRegionSchema, many=True)
    signatures_by_constituency = Nested(SignaturesByConstituencySchema, many=True)



class PetitionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Petition
        exclude = ['initial_data', 'latest_data', 'db_updated_at']

class PetitionNestedSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Petition
        include_relationships = True

    records = Nested(RecordSchema, many=True)



class ModelUtils():

    @classmethod
    def validate_geography_choice(cls, instance, key, value):
        model = instance.__class__
        choices = dict(model.CODE_CHOICES)
        
        try:
            choices[value]
        except KeyError:
            value = model.CODE_LOOKUP[value]
        
        return value