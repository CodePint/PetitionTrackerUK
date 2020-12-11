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
    trend_index = db.Column(Integer, default=None)
    growth_rate = db.Column(Float, default=0)
    record_rel_attrs = {"lazy": "dynamic", "back_populates": "petition", "cascade": "all,delete-orphan"}
    records = relationship(lambda: Record, **record_rel_attrs)

    # handles requests for petition data scraping
    remote = RemotePetition

    def __repr__(self):
        template = "<id: {}, signatures: {}, created_at: {}>"
        return template.format(self.id, self.signatures, self.db_created_at)

    def __str__(self):
        template = "id: {}, action: {}"
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
        discovered = ids or cls.discover(state=state)
        if not any(discovered):
            logger.info("no new petitions discovered")
            return discovered

        logger.info(f"fetching detailed remote data for new petitions: {discovered}")
        responses = cls.remote.async_get(petitions=discovered, max_retries=3).get("success")
        if not any(responses):
            raise RuntimeError(f"failed to fetch detailed data for petitions: {discovered}")

        logger.info("initializing petition objects")
        populated = []
        for r in responses:
            petition = Petition(id=r.data["data"]["id"], initial_data=r.data)
            petition.sync(r.data, r.timestamp)
            populated.append(petition)

        petition_ids = [p.id for p in populated]
        logger.info("bulk saving petitions")
        db.session.bulk_save_objects(populated)
        db.session.commit()
        logger.info(f"bulk save completed, populated IDs: {petition_ids}")

        return petition_ids

    # find remote petitions that have yet to be onboarded
    @classmethod
    def discover(cls, state):
        query = cls.remote.async_query(state=state, max_retries=3)
        if not any(query["success"]):
            raise RuntimeError(f"query response empty, failures: '{len(query['failed'])}'")

        logger.info("filtering query result against existing petition IDs")
        query = cls.remote.unpack_query(query)
        queried = {item["id"] for item in query["success"]}
        existing = {p[0] for p in Petition.query.with_entities(Petition.id).all()}
        discovered = (queried - existing)

        logger.info(f"{len(discovered)} petitions discovered")
        return discovered


    # poll all petitions which match where param and kwargs opts (or provide list)
    # signatures_by = True for full geo records, signatures_by = False for basic total records
    @classmethod
    def poll(cls, petitions=[], contition="all", geographic=False, **filters):
        petitions = petitions or cls.build_poll_query(contition=contition, **filters).all()
        logger.info(f"Petitions returned from query: {len(petitions)}")
        if not any(petitions):
            return []

        responses = cls.remote.async_get(petitions=petitions, max_retries=3)
        logger.info(f"petitions returned from async poll: {len(responses['success'])} ")
        if not any(responses["success"]):
            raise RuntimeError(f"no poll responses, failures: {len(responses['failed'])}")

        polled = [r.petition.sync(r.data, r.timestamp) for r in responses["success"]]
        db.session.flush()

        return cls.save_poll(polled, geographic, **filters)

    # create a list of petitions to poll based on query params
    @classmethod
    def build_poll_query(cls, condition="any", **kwargs):
        valid_conditions = ["trending", "signatures", "any"]
        if not condition in valid_conditions:
            raise ValueError(f"Invalid condition value: '{condition}', allowed: '{valid_conditions}'")

        query = cls.query.filter_by(state="O", archived=False)
        if condition == "trending":
            threshold = kwargs.get("threshold", Setting.get("trending_threshold", type=int))
            petitions = query.order_by(Petition.trend_index.asc()).limit(threshold)
        elif condition == "signatures":
            threshold = kwargs.get("threshold", Setting.get("signatures_threshold", type=int))
            if kwargs.get("lt"):
                petitions = query.filter(Petition.signatures < threshold)
            else:
                petitions = query.filter(Petition.signatures > threshold)
        return query

    @classmethod
    def save_poll(cls, petitions, geographic, **filters):
        logger.info("saving base poll")

        recorded = cls.save_base_data(petitions)
        if geographic:
            logger.info("saving geo poll")
            recorded = cls.save_geo_data(recorded, **filters)

        logger.info("commiting poll!")
        db.session.commit()
        logger.info("completed poll!")

        return recorded

    # save basic record without detailed geographic signatures
    @classmethod
    def save_base_data(cls, petitions):
        records = []
        for petition in petitions:
            logger.debug("handling base data for ID: {}".format(petition.id))
            records.append(Record.init_dict(petition))

        logger.info("bulk inserting base records! ({})".format(len(records)))
        insert_stmt = postgresql.insert(Record).values(records).returning(Record.id)
        inserted = db.session.execute(insert_stmt).fetchall()
        inserted_ids = [id[0] for id in inserted]

        logger.info("record insertion complete - flushing and fetching result")
        db.session.flush()
        recorded = Record.query.filter(Record.id.in_(inserted_ids)).all()
        logger.info("base records saved: {}".format(len(recorded)))

        return recorded

    # upgrade basic record to detailed geographic signatures record
    # can specify a minimum growth filter to determine if record shoudld be upgraded
    @classmethod
    def save_geo_data(cls, records, min_growth=0, **filters):
        if min_growth:
            # Integration/Testing needed
            pass

        signatures_by = []
        for r in records:
            logger.debug("building geo data for ID: {}".format(r.petition.id))
            attributes = r.petition.latest_data["data"]["attributes"]
            signatures_by += r.build(attributes)

        logger.info("bulk saving geo record")
        db.session.bulk_save_objects(signatures_by)
        logger.info("bulk save completed - flushing db")
        db.session.flush()

        return records

    # reindex trending petitions from a poll event
    @classmethod
    def reindex_trending(cls, period={"minutes": 60}, max_range={"minutes": 30}, event="global_poll"):
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
            petition.trend_index = index + 1

        missing = Petition.query.filter(Petition.id.notin_([p.id for p in trending]))
        logger.info(f"petitons missing poll data: {len(missing)}, setting defaults")
        for petition in missing:
            petition.growth_rate = 0
            petition.trend_index = None

        logger.info("trending updating - commiting result")
        db.session.add_all(trending + missing)
        db.session.commit()
        return {"trending": trending, "missing": missing}

    # sync remote petition data with petition columns and updated latest_data
    def sync(self, data, timestamp):
        attributes = data["data"]["attributes"]
        self.polled_at = timestamp
        self.url = data["links"]["self"]
        self.archived = data["data"]["type"] == "archived-petition"
        self.pt_closed_at = attributes["closed_at"]
        self.pt_updated_at = attributes["updated_at"]
        self.pt_rejected_at = attributes["rejected_at"]
        self.signatures = attributes["signature_count"]
        self.state = attributes["state"]
        self.update(**attributes)
        self.latest_data = data

        return self

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

    # returns a query object for the petitions records
    def ordered_records(self, order="DESC", geographic=None):
        if order == "DESC":
            records = self.records.order_by(Record.timestamp.desc())
        if order == "ASC":
            records = self.records.order_by(Record.timestamp.asc())

        if geographic is not None:
            records = records.filter_by(geographic=geographic)
        raise ValueError("Invalid order param, Must be 'DESC' or 'ASC'")

    # return the petitions latest record (geographic or basic)
    def latest_record(self, geographic=True):
        return self.ordered_records().filter_by(geographic=geographic).first()

    # update attributes with kwargs
    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self


class Record(db.Model):
    __tablename__ = "record"
    ts = synonym("timestamp")

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

    def get_sig_relation(self, geo):
        return getattr(self, "signatures_by_" + geo)

    @classmethod
    def code_key(cls, geo):
        return "code" if geo == "country" else "ons_code"

    @classmethod
    def get_sig_model(cls, geography):
        return getattr(sys.modules[__name__], ("SignaturesBy" + geography.capitalize()))

    @classmethod
    def get_sig_table(cls, geography):
        return cls.get_sig_model().__table__

    @classmethod
    def signature_attributes(cls, *geographies):
        attrs = {}
        for geo in geographies:
            attrs[geo] = {}
            attrs[geo]["model"] = cls.get_sig_model(geo)
            attrs[geo]["table"] = attrs[geo]["model"].__table__
            attrs[geo]["name"] = attrs[geo]["model"].__tablename__
            attrs[geo]["relationship"] = getattr(cls, attrs[geo]["name"])
            attrs[geo]["schema_class"] = SignaturesBySchema.schema_for(geo)
        return attrs

    @classmethod
    def get_sig_choice(cls, geography, key_or_value):
        model = cls.get_sig_model(geography)
        choices = dict(model.CODE_CHOICES)
        try:
            choices[key_or_value.upper()]
            code = key_or_value.upper()
        except KeyError:
            code = model.CODE_LOOKUP[key_or_value]

        return {"code": code, "value": choices[code]}

    @classmethod
    def validate_locale_choice(cls, inst, key, value):
        try:
            dict(inst.__class__.CODE_CHOICES)[value]
        except KeyError:
            value = inst.__class__.CODE_LOOKUP[value]
        return value

    @classmethod
    def closest_distinct(cls, timestamp, petitions=[], geographic=None, order_by="DESC", lazy=False):
        query = Record.query.distinct(Record.petition_id)
        if petitions:
            query = query.filter(Record.petition_id.in_([p.id for p in petitions]))
        if geographic is not None:
            query = query.filter_by(geographic=geographic)

        ordering = getattr(Record.timestamp, order_by.lower())()
        query = query.filter(Record.timestamp < timestamp)
        query = query.from_self().order_by(ordering())
        return query if lazy else query.all()

    @classmethod
    def filter_min_growth(cls, records, diff, geographic=True):
        petitions = [r.petition for r in records]
        distinct_kwargs = {"petitions": petitions, "geographic": geographic, "lazy": True}
        distinct_query = Record.closest_distinct(dt.now(), **distinct_kwargs)
        prev_records = distinct_query.order_by(Record.petition_id).desc().all()
        curr_records = sorted(records, key=lambda r: r.petition_id)

        filtered = []
        for prev, curr in zip(prev_records, curr_records):
                if curr.signatures - prev.signatures > diff:
                    filtered.append(curr)

        return filtered

    # create a new record for the petition
    def build(self, attrs):
        make_conf = lambda d, p: {k.replace(p, ""): v for k, v in d.items() if k.startswith(p)}
        config = make_conf(attrs, "signatures_by_")

        built = []
        for geo in list(config.keys()):
            model = Record.get_sig_model(geo)
            code_key, count_key = self.code_key(geo), "signature_count"
            for locale in config[geo]:
                locale = model(
                    record_id=self.id,
                    code=locale[code_key],
                    count=locale["signature_count"]
                )
                built.append(locale)

        self.petition.geo_saved_at = self.timestamp
        self.geographic = True
        return built

    @classmethod
    def init_dict(cls, petition):
        return {
            "petition_id": petition.id,
            "signatures": petition.signatures,
            "timestamp": petition.polled_at,
            "db_created_at": sqlfunc.now()
        }


    # short hand query helper query for signature geography + code or name
    def signatures_by(self, geo, locale):
        model = Record.get_git_model(geo)
        choice = Record.get_sig_choice(geo, locale)
        try:
            return self.get_sig_relation(geo).filter(model.code == choice["code"]).one()
        except sqlalchemy.orm.exc.NoResultFound:
            return None

    def signatures_comparison(self, record_schema, attrs):
        comparison = record_schema.dump(self)
        for geo in attrs.keys():
            relation = self.get_sig_relation(geo)
            model, locales = attrs[geo]["model"], attrs[geo]["locales"]
            filtered = relation.filter(model.code.in_(locales))

            geo_name, geo_schema = attrs[geo]["name"], attrs[geo]["schema"]
            comparison[geo_name] = [geo_schema.dump(sig) for sig in filtered.all()]

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
        return Record.validate_locale_choice(self, key, value)

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
        return Record.validate_locale_choice(self, key, value)

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
        return Record.validate_locale_choice(self, key, value)

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
    def schema_for(cls, geography):
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
