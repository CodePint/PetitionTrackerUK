import sqlalchemy
from sqlalchemy_utils import *
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy.dialects import postgresql
from sqlalchemy import (
    and_,
    inspect,
    Integer,
    Float,
    Boolean,
    String,
    ForeignKey,
    DateTime,
    UniqueConstraint
)
from flask import current_app as c_app
from marshmallow import fields as ma_fields
from marshmallow_sqlalchemy.fields import Nested
from marshmallow_sqlalchemy import SQLAlchemySchema, SQLAlchemyAutoSchema, auto_field
from requests.structures import CaseInsensitiveDict as LazyDict

from application import db
from application.models import Setting, Event, Task, TaskRun
from .remote import RemotePetition
from application.tracker.geographies.choices.regions import REGIONS
from application.tracker.geographies.choices.countries import COUNTRIES
from application.tracker.geographies.choices.constituencies import CONSTITUENCIES

import sys
import requests
import json
import datetime
from math import ceil, floor
from datetime import datetime as dt
from datetime import timedelta

import logging

logger = logging.getLogger(__name__)

class Petition(db.Model):
    __tablename__ = "petition"

    STATE_CHOICES = [
        ("C", "closed"),
        ("R", "rejected"),
        ("O", "open"),
    ]
    STATE_LOOKUP = LazyDict({v: k for k, v in dict(STATE_CHOICES).items()})

    id = db.Column(Integer, primary_key=True, autoincrement=False)
    state = db.Column(ChoiceType(STATE_CHOICES), nullable=False)
    archived = db.Column(Boolean, default=False, nullable=False)
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
    db_created_at = db.Column(DateTime, default=sqlfunc.now())
    db_updated_at = db.Column(DateTime, default=sqlfunc.now(), onupdate=sqlfunc.now())
    initial_data = db.Column(JSONType)
    latest_data = db.Column(JSONType)
    trend_position = db.Column(Integer, default=None)
    growth_rate = db.Column(Float, default=0)
    record_rel_attrs = {"lazy": "dynamic", "back_populates": "petition", "cascade": "all,delete-orphan"}
    records = relationship(lambda: Record, **record_rel_attrs)

    # handles requests for petition data scraping
    remote = RemotePetition

    def __repr__(self):
        template = "<id: {}, signatures: {}, created_at: {}>"
        return template.format(self.id, self.signatures, self.db_created_at)

    def __str__(self):
        template = "petiton id: {}, action: {}"
        return template.format(self.id, self.action)

    # work around for broken choice validation in sqlalchemy utils
    # also allows case agnostic value/key of the state tuple
    @validates("state")
    def validate_state_choice(self, key, state):
        try:
            state = Petition.STATE_LOOKUP[state]
        except KeyError:
            dict(Petition.STATE_CHOICES)[state]

        return state

    @classmethod
    def str_or_datetime(cls, time):
        return dt.strptime(time, "%d-%m-%YT%H:%M:%S") if isinstance(time, str) else time

    # onboard multiple remote petitions from the result of a query
    @classmethod
    def populate(cls, ids=[], state="open"):
        fetched = ids or cls.find_new(state=state)
        if not any(fetched):
            logger.info("no new petitions found")
            return fetched

        logger.info(f"fetching detailed remote data for new petitions: {fetched}")
        responses = cls.remote.async_fetch(ids=fetched, max_retries=3).get("success")

        if not any(responses):
            raise RuntimeError(f"Failed to fetch detailed data for petitions: {fetched}")

        logger.info("initializing petition objects")
        populated = []
        for r in responses:
            petition = Petition(id=r.id, initial_data=r.data, latest_data=r.data)
            petition.sync_column_data()
            populated.append(petition)

        petition_ids = [p.id for p in populated]
        logger.info("bulk saving petitions")
        db.session.bulk_save_objects(populated)

        logger.info(f"petitions saved successfully, populated IDs: {petition_ids}")
        return petition_ids

    @classmethod
    def find_new(cls, state):
        query = cls.remote.async_query(state=state)
        if any(query["success"]):
            logger.info(f"remote query completed, matching petitions found: '{len(query['success'])}'")
        else:
            raise RuntimeError(f"Query response empty, failures: '{len(query['failed'])}'")

        logger.info("filtering query result against existing petition IDs")
        queried = {item["id"] for item in query["success"]}
        existing = {p[0] for p in Petition.query.with_entities(Petition.id).all()}

        return (queried - existing)

    # poll all petitions which match where param and kwargs opts (or provide list)
    # signatures_by = True for full geo records, signatures_by = False for basic total records
    # if commit = False, poll will return the filtered responses with attached petition objs
    @classmethod
    def poll(cls, petitions=[], contition="all", geographic=True, commit=True, **kwargs):
        petitions = petitions or cls.build_poll_query(contition=contition, **kwargs).all()
        logger.info(f"Petitions returned from query: {len(petitions)}")

        if any(petitions):
            responses = cls.remote.async_poll(petitions=petitions, max_retries=3)
            logger.info(f"Petitions returned from async poll: {len(responses['success'])} ")
        else:
            return []

        if any(responses["success"]):
            petitions = {"petitions": [r.petition for r in responses["success"]]}
            return cls.handle_poll(geographic=geo, **petitions) if commit else responses
        else:
            raise RuntimeError(f"No poll responses, failures: {len(responses['failed'])}")

    @classmethod
    def handle_poll(cls, petitions, geographic):
        logger.info("saving base poll")
        recorded = cls.save_base_data(petitions)

        if geographic:
            logger.info("saving geo poll")
            recorded = cls.save_geo_data(records=recorded)

        logger.info("commiting poll!")
        db.session.commit()
        logger.info("completed poll!")

        return recorded

    @classmethod
    def save_base_data(cls, petitions):
        records = []
        for petition in petitions:
            logger.debug("handling base data for ID: {}".format(petition.id))
            petition.sync_column_data()
            records.append(Record.init_dict(petition))

        db.session.flush()
        logger.info("bulk inserting base records! ({})".format(len(records)))
        insert_stmt = postgresql.insert(Record).values(records).returning(Record.id)

        inserted = db.session.execute(insert_stmt).fetchall()
        inserted_ids = [id[0] for id in inserted]

        logger.info("record insertion completed - flushing db")
        db.session.flush()
        recorded = Record.query.filter(Record.id.in_(inserted_ids)).all()
        logger.info("base records saved: {}".format(len(recorded)))

        return recorded

    @classmethod
    def save_geo_data(cls, records, min_increase=None):
        built = []
        for record in records:
            logger.debug("handling geo datas for ID: {}".format(record.petition.id))
            signatures_by = record.build()
            built.append(signatures_by)

        built = [sigs_by for record in built for sigs_by in record]
        logger.info("bulk saving geo records! ({})".format(built))
        db.session.bulk_save_objects(built)

        logger.info("bulk save completed - flushing db")
        db.session.flush()

        return records

    @classmethod
    def build_poll_query(cls, condition="any", **kwargs):
        valid_conditions = ["trending", "signatures", "any"]
        if not condition in valid_conditions:
            raise ValueError(f"Invalid condition value: '{condition}', allowed: '{valid_conditions}'")

        query = cls.query.filter_by(state="O", archived=False)
        if condition == "trending":
            threshold = kwargs.get("threshold", Setting.get("trending_threshold", type=int))
            petitions = query.order_by(Petition.trend_pos.asc()).limit(threshold)
        elif condition == "signatures":
            threshold = kwargs.get("threshold", Setting.get("signatures_threshold", type=int))
            if kwargs.get("lt"):
                petitions = query.filter(Petition.signatures < threshold)
            else:
                petitions = query.filter(Petition.signatures > threshold)

        return query

    @classmethod
    def update_trending(cls, period={"minutes": 60}, max_range={"minutes": 30}, event="global_poll"):
        event_query = {"ts": (dt.now - timedelta(**period)), "max_range": timedelta(**max_range)}
        event = Event.closest(name=event, **event_query)
        logger.info(f"using {event.name}, which ran at: {event.ts}")

        prev_records = Record.closest_distinct(event.ts, order_by="DESC")
        logger.info(f"previous distinct records found: {len(prev_records)}")

        comparison = []
        logger.info("finding growth rates")
        for record in prev_records:
            petition = record.petition
            sig_diff = petition.signatures - record.signatures
            time_diff = round((petition.polled_at - record.timestamp).total_seconds())
            petition.growth_rate = (sig_diff / (time_diff / 60))
            comparison.append(petition)

        logger.info("updating trend pos")
        trending = comparison.sort(key=lambda p: p.growth_rate)
        for index, petition in enumerate(trending):
            petition.trend_pos = index + 1

        missing = Petition.query.filter(Petition.id.notin_([p.id for p in trending]))
        logger.info(f"petitons missing poll data: {len(missing)}, setting defaults")
        for petition in missing:
            petition.growth_rate = 0
            petition.trend_pos = None

        logger.info("trending updating - commiting result")
        db.session.add_all(trending + missing)
        db.session.commit()

        return {"trending": trending, "missing": missing}

    def sync_column_data(self):
        attributes = self.latest_data["data"]["attributes"]
        self.polled_at = self.latest_data["timestamp"]
        self.archived = self.latest_data["archived"]
        self.pt_closed_at = attributes["closed_at"]
        self.pt_updated_at = attributes["updated_at"]
        self.pt_rejected_at = attributes["rejected_at"]
        self.signatures = attributes["signature_count"]
        self.state = attributes["state"]

        self.update(attributes)

    def populate_self(self):
        return Petition.populate(ids=[self.id])

    def poll_self(self, commit=True, geo=True):
        return Petition.poll(petitions=[self.id], commit=commit, geo=geo)

    def fetch_self(self, raise_404=True):
        return Petition.remote.get(id=self.id, raise_404=raise_404)

    def get_closest_record(self, to, geographic=True):
        query = self.records.filter_by(geographic=geographic)
        query = query.filter(Record.timestamp < Petition.str_or_datetime(to))
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
        query = self.records.filter(Record.timestamp > (now - timedelta(**since)))
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

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self


class Record(db.Model):
    __tablename__ = "record"
    id = db.Column(Integer, primary_key=True)
    petition_id = db.Column(Integer, ForeignKey(Petition.id, ondelete="CASCADE"), index=True, nullable=False)
    timestamp = db.Column(DateTime, index=True, nullable=False)
    db_created_at = db.Column(DateTime, default=sqlfunc.now(), nullable=False)
    signatures = db.Column(Integer, nullable=False)
    geographic = db.Column(Boolean, default=False)
    petition = relationship(Petition, back_populates="records")
    sigs_rel_attrs = {"lazy": "dynamic", "back_populates": "record", "cascade": "all,delete-orphan"}
    signatures_by_country = relationship(lambda: SignaturesByCountry, **sigs_rel_attrs)
    signatures_by_region = relationship(lambda: SignaturesByRegion, **sigs_rel_attrs)
    signatures_by_constituency = relationship(lambda: SignaturesByConstituency, **sigs_rel_attrs)

    def __repr__(self):
        template = "<record_id: {}, petition_id: {}, timestamp: {}, signatures: {}>"
        return template.format(self.id, self.petition_id, self.timestamp, self.signatures)

    def __str__(self):
        template = "Total signatures for petition ID: {}, at {}: {}"
        return template.format(self.petition_id, self.timestamp, self.signatures)

    @classmethod
    def validate_geography_choice(cls, instance, key, value):
        model = instance.__class__
        choices = dict(model.CODE_CHOICES)

        try:
            choices[value]
        except KeyError:
            value = model.CODE_LOOKUP[value]

        return value

    @classmethod
    def get_sig_model_table(cls, geography):
        model = getattr(sys.modules[__name__], ("SignaturesBy" + geography.capitalize()))
        table = model.__table__
        return model, table

    @classmethod
    def init_dict(cls, petition):
        return {
            "petition_id": petition.id,
            "signatures": petition.signatures,
            "timestamp": petition.polled_at,
            "db_created_at": sqlfunc.now()
        }

    @classmethod
    def signature_model_attributes(cls, geographies):
        attributes = {}
        for geo in geographies:
            model, table = cls.get_sig_model_table(geo)
            attributes[geo] = {
                "model": model,
                "table": table,
                "name": model.__tablename__,
                "relationship": getattr(cls, model.__tablename__),
                "schema_class": SignaturesBySchema.get_schema_for(geo),
            }
        return attributes

    @classmethod
    def get_sig_choice(cls, geography, key_or_value):
        model, table = cls.get_sig_model(geography)
        choices = dict(model.CODE_CHOICES)

        try:
            choices[key_or_value.upper()]
            code = key_or_value.upper()
        except KeyError:
            code = model.CODE_LOOKUP[key_or_value]

        value = choices[code]
        return {"code": code, "value": value}

    @classmethod
    def parse_build_input(cls, attributes):
        return {
            key.replace("signatures_by_", ""): val
            for key, val in attributes.items() if key.startswith("signatures_by_")
        }

    @classmethod
    def closest_distinct(cls, timestamp, order_by="DESC", lazy=False):
        ordering = getattr(Record.ts, order_by.lower())()
        query = Record.query.distinct(Record.petition_id)
        query = query.filter(Record.timestamp < timestamp)
        query = query.from_self().order_by(ordering())
        return query if lazy else query.all()

    # create a new record for the petition
    def build(self, attributes={}):
        attributes = attributes or self.petition.latest_data["data"]["attributes"]
        attributes = Record.parse_build_input(attributes)

        created = []
        if any(attributes.values()):
            self.geographic = True
            for geo in list(attributes.keys()):
                model, table = Record.get_sig_model_table(geo)
                code = "code" if geo == "country" else "ons_code"
                for locale in attributes[geo]:
                    created.append(model(
                        record_id=self.id,
                        code=locale[code],
                        count=locale["signature_count"]
                    ))

        return created

    # short hand query helper query for signature geography + code or name
    def signatures_by(self, geography, locale):
        model, table = Record.get_sig_model(geography)
        relation = self.sig_relation(geography)
        choice = Record.get_sig_choice(geography, locale)

        try:
            return relation.filter(model.code == choice["code"]).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return None

    def sig_relation(self, geography):
        return getattr(self, "signatures_by_" + geography)

    def signatures_comparison(self, schema, attrs):
        comparison = schema.dump(self)
        for geo in attrs.keys():
            relation = self.sig_relation(geo)
            filtered = relation.filter(attrs[geo]["model"].code.in_(attrs[geo]["locales"])).all()
            comparison[attrs[geo]["name"]] = [attrs[geo]["schema"].dump(sig) for sig in filtered]
        return comparison



class SignaturesByCountry(db.Model):
    __tablename__ = "signatures_by_country"
    __table_args__ = (
        db.UniqueConstraint(
            "record_id", "iso_code",
            name="uniq_sig_country_for_record"
        ),
    )

    CODE_CHOICES = COUNTRIES
    CODE_LOOKUP = LazyDict({v: k for k, v in dict(CODE_CHOICES).items()})
    code = synonym("iso_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"), index=True, nullable=False)
    iso_code = db.Column(ChoiceType(CODE_CHOICES), index=True, nullable=False)
    count = db.Column(Integer, default=0)
    record = relationship(Record, back_populates="signatures_by_country")

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates("iso_code")
    def validate_code_choice(self, key, value):
        return ModelUtils.validate_geography_choice(self, key, value)

    def __str__(self):
        return "{} - {}".format(self.code.value, self.count)

    def __repr__(self):
        template = "<id: {}, code: {}, count: {}>"
        return template.format(self.id, self.code, self.count)



class SignaturesByRegion(db.Model):
    __tablename__ = "signatures_by_region"
    __table_args__ = (
        db.UniqueConstraint(
            "record_id", "ons_code",
            name="uniq_sig_region_for_record"
        ),
    )
    CODE_CHOICES = REGIONS
    CODE_LOOKUP = LazyDict({v: k for k, v in dict(CODE_CHOICES).items()})
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"), index=True, nullable=False)
    ons_code = db.Column(ChoiceType(CODE_CHOICES), index=True, nullable=False)
    count = db.Column(Integer, default=0)
    record = relationship(Record, back_populates="signatures_by_region")


    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates("ons_code")
    def validate_code_choice(self, key, value):
        return ModelUtils.validate_geography_choice(self, key, value)

    def __str__(self):
        return "{} - {}".format(self.code.value, self.count)

    def __repr__(self):
        template = "<id: {}, code: {}, count: {}>"
        return template.format(self.id, self.code, self.count)



class SignaturesByConstituency(db.Model):
    __tablename__ = "signatures_by_constituency"
    __table_args__ = (
        db.UniqueConstraint(
            "record_id", "ons_code",
            name="uniq_sig_constituency_for_record"
        ),
    )
    CODE_CHOICES = CONSTITUENCIES
    CODE_LOOKUP = LazyDict({v: k for k, v in dict(CODE_CHOICES).items()})
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"), index=True, nullable=False)
    ons_code = db.Column(ChoiceType(CODE_CHOICES), index=True,  nullable=False)
    count = db.Column(Integer, default=0)
    record = relationship(Record, back_populates="signatures_by_constituency")


    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates("ons_code")
    def validate_code_choice(self, key, value):
        return ModelUtils.validate_geography_choice(self, key, value)

    def __str__(self):
        return "{} - {}".format(self.code.value, self.count)

    def __repr__(self):
        template = "<id: {}, code: {}, count: {}>"
        return template.format(self.id, self.code, self.count)




# model deserialisation schemas
class SignaturesBySchema(SQLAlchemyAutoSchema):
    class Meta:
        include_relationships = True
        exclude = ["id"]

    @classmethod
    def get_schema_for(cls, geography):
        return getattr(
            sys.modules[__name__],
            "SignaturesBy{}{}".format(geography.capitalize(), "Schema")
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
        exclude = [
            "db_created_at",
            "geographic",
            "signatures",
            "by_country",
            "by_region",
            "by_constituency"
        ]

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
        exclude = ["initial_data", "latest_data", "db_updated_at"]

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