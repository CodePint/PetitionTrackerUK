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
from application.models import Task, TaskRun, TaskLog
from .remote import RemotePetition
from .utils import ViewUtils

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
    def get_or_404(cls, id):
        petition = Petition.query.get(id)
        return petition or ViewUtils.json_abort(404, "Petition ID: {}, not found".format(id))

    @classmethod
    def filter_sigs_by(cls, attributes):
        return { 
            key.replace('signatures_by_', ''): val
            for key, val in attributes.items() if key.startswith('signatures_by_')
        }

    @classmethod
    def get_setting(cls, *args, **kwargs):
        return current_app.settings.get(*args, **kwargs)

    # onboard multiple remote petitions from the result of a query
    @classmethod
    def populate(cls, state="open", query=[], signatures_by=False, count=False, archived=False, **kwargs):
        query = cls.remote.query(count=count, query=query, state=state, archived=archived)
        ids = [item['id'] for item in query if not cls.query.get(item['id'])]
        remotes = cls.remote.async_get(ids, retries=3).get('success')
        petitions = [cls.onboard(remote=r, signatures_by=signatures_by) for r in remotes]

        return petitions

    # onboard a remote petition by id
    @classmethod
    def onboard(cls, id=None, remote=None, signatures_by=False, **kwargs):
        remote = remote or cls.remote.get(id, raise_404=True)

        print("onboarding petition ID: {}".format(id))
        attributes = remote.data['data']["attributes"]
        total_sigs = attributes['signature_count']
        params = cls.remote.deserialize(remote.data)
        petition = Petition(**params)
        
        if signatures_by:
            petition.geo_polled_at = remote.timestamp
        else:
            petition.polled_at = remote.timestamp
        
        db.session.add(petition)
        record = Record.create(
            petition_id=petition.id,
            timestamp=remote.timestamp,
            sigs_by=cls.filter_sigs_by(attributes),
            total_sigs=total_sigs,
            build_sigs_by=signatures_by
        )

        db.session.commit()
        return petition

    # poll all petitions which match where param and kwargs opts
    # signatures_by = True for full geo records, signatures_by = False for basic total records
    # if commit = False, poll will return the filtered responses with attached petition objs
    @classmethod
    def poll(cls, where="all", signatures_by=False, commit=True, **kwargs):
        valid_where_values = ["trending", "signatures_gt", "signatures_lt", "all"]
        if not where in valid_where_values:
            raise ValueError("Invalid param: 'where'. Valid values: {}".format(valid_where_values))

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
        
        responses = cls.remote.async_poll(petitions, retries=3).get('success')
        return [r.petition.commit_poll(r, signatures_by) for r in responses] if commit else responses
    
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
    def update_trending(cls, task_name="poll_total_sigs_task", before={"minutes": 60}, ts_range=2.5):
        last_run = Task.get_last_run(name=task_name, before=before)
        if not last_run:
            raise RuntimeError("No run found before: {}".format(before))

        compare_to = round((dt.now() - last_run.finished_at).total_seconds() / 60)
        if not math.ceil(compare_to / 60) not in range(1, 13):
            raise RuntimeError("Comparison interval must be in range '1 to 12 hours'")

        gt, lt = compare_to + ts_range, compare_to - ts_range
        petitions = Petition.get_all_with_distinct_record_at(gt=gt, lt=lt)
        not_found = Petition.query.filter(Petition.id.notin_([p.id for p in petitions])).all()

        def sort_func(response):
            petition = response.petition
            curr_count = response.data['data']['attributes']['signature_count']
            petition.growth = curr_count - petition.distinct_record.signatures
            return petition.growth

        responses = cls.remote.async_poll(petitions, retries=3).get('success')
        responses.sort(key=lambda r: sort_func(r))

        for index, resp in enumerate(responses):
            resp.petition.trend_pos = index + 1
        
        for petition in not_found:
            petition.trend_pos = 0

        db.session.commit()
        return responses

    # poll the petition instance, optional record commit and record build type (signatures_by) 
    def poll_self(self, signatures_by=True, commit=True, **kwargs):
        response = Petition.remote.get(self.id, raise_404=True)
        if commit:
            return self.commit_poll(response, signatures_by)
        else:
            return response

    # build record from poll response, must specify record build type (signatures_by) 
    def commit_poll(self, response, signatures_by):
        attributes = response.data['data']["attributes"]
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
            sigs_by=Petition.filter_sigs_by(attributes),
            total_sigs=attributes['signature_count'],
            build_sigs_by=signatures_by
        )

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

    def query_records_between(self, lt, gt):
        query = self.records.filter(Record.timestamp > gt)
        query = query.filter(and_(Record.timestamp < lt))
        return query.order_by(Record.timestamp.desc())

    def query_record_at(self, timestamp, at):
        if isinstance(timestamp, str):
            timestamp = dt.strptime(timestamp, "%d-%m-%YT%H:%M:%S")
        query = self.records.filter(Record.timestamp < timestamp)
        return query.order_by(Record.timestamp.desc())

    # since ex: {'hours': 12}, {'days': 7}, {'month': 1}
    def query_records_since(self, since, now=None):
        now = dt.strptime(now, "%d-%m-%YT%H:%M:%S") if now else dt.now()
        ago = now - datetime.timedelta(**since)
        query = self.records.filter(Record.timestamp > ago)
        return query.order_by(Record.timestamp.desc())

    def ordered_records(self, order="DESC"):
        if order == "DESC":
            return self.records.order_by(Record.timestamp.desc())
        if order == "ASC":
            return self.records.order_by(Record.timestamp.asc())
        
        raise ValueError("Invalid order param, Must be 'DESC' or 'ASC'")
    
    def latest_record(self):
        return self.ordered_records().first()


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
        template = 'Total signatures for petition id: {}, at {}: {}'
        return template.format(self.petition_id, self.timestamp, self.signatures)
    
    @classmethod
    def get_sig_model(cls, geography):
        return getattr(sys.modules[__name__], ('SignaturesBy' + geography.capitalize()))   

    @classmethod
    def get_sig_model_table(cls, geography):
        model = cls.get_sig_model(geography)
        table = model.__table__
        return model, table

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
    def create(cls, petition_id, timestamp, sigs_by, total_sigs, build_sigs_by):
        print("creating record for petition ID: {}".format(petition_id))
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
        exclude = ["db_created_at", "signatures", "by_country", "by_region", "by_constituency"]
    
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