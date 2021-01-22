import sqlalchemy
from flask import current_app
from sqlalchemy_utils import *
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func as sqlfuncgen
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import (
    relationship,
    synonym,
    validates,
    reconstructor,
    joinedload,
    eagerload
)
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

from marshmallow import fields as ma_fields
from marshmallow_sqlalchemy.fields import Nested
from marshmallow_sqlalchemy import SQLAlchemySchema, SQLAlchemyAutoSchema, auto_field
from requests.structures import CaseInsensitiveDict as LazyDict

from application import db
from application.models import Setting, Event, Task, TaskRun
from application.tracker.remote import RemotePetition
from application.tracker.geographies.choices.regions import REGIONS
from application.tracker.geographies.choices.countries import COUNTRIES
from application.tracker.geographies.choices.constituencies import CONSTITUENCIES
from application.tracker.exceptions import PetitionsNotFound, RecordsNotFound

from math import ceil, floor
from datetime import datetime as dt
from datetime import timedelta
from copy import deepcopy
from collections.abc import Iterable
import operator as py_operator
import datetime, json, sys, logging

get_operator =  lambda opr: getattr(py_operator, opr)
plainto_tsquery = lambda qs: sqlfuncgen.plainto_tsquery("english", qs)

def match_text(_cls, column, value):
    column = getattr(_cls, column)
    text_query = plainto_tsquery(value)
    return column.op("@@")(text_query)

logger = logging.getLogger(__name__)



class Petition(db.Model):
    __tablename__ = "petition"

    STATE_CHOICES = [
        ("C", "closed"),
        ("R", "rejected"),
        ("O", "open")
    ]

    TEXT_COLS = ["action", "background", "additional_details", "creator_name"]
    STATE_VALUES = [v for v in dict(STATE_CHOICES).values()]
    STATE_LOOKUP = LazyDict({v: k for k, v in dict(STATE_CHOICES).items()})
    record_relation_attributes = {"lazy": "dynamic", "back_populates": "petition", "cascade": "all,delete-orphan"}

    id = db.Column(Integer, primary_key=True, autoincrement=False)
    state = db.Column(ChoiceType(STATE_CHOICES), nullable=False)
    archived = db.Column(Boolean, default=False, nullable=False)
    action = db.Column(String(512), index=True, nullable=False)
    signatures = db.Column(Integer, nullable=False)
    url = db.Column(String(2048), index=True, unique=True)
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
    records = relationship(lambda: Record, **record_relation_attributes)
    date = synonym("pt_created_at")

    remote = RemotePetition

    def __repr__(self):
        template = "<petition_id: {}, signatures: {}, created_at: {}>"
        return template.format(self.id, self.signatures, self.db_created_at)

    # work around for broken choice validation in sqlalchemy utils
    # also allows case agnostic key/value use of the state tuple
    @validates("state")
    def validate_state_choice(self, key, state):
        return self.validate_state(state)

    # order_by ex: {"signatures": "DESC"}
    @classmethod
    def order_attr(cls, order_by):
        column, direction = list(order_by.items())[0]
        return getattr(getattr(cls, column), direction.lower())

    @classmethod
    def validate_state(cls, state):
        try:
            state = cls.STATE_LOOKUP[state]
        except KeyError:
            dict(cls.STATE_CHOICES)[state]
        return state

    @classmethod
    def lazy_strptime(cls, time, fmt="%d-%m-%YT%H:%M:%S"):
        return dt.strptime(time, fmt) if type(time) is str else time

    # expressions: {"signatures": {"gt": 10_000}, "created_at": {"le": 2020/01/01}}
    @classmethod
    def filter_expression(cls, **expressions):
        filters = []
        for col, expr in expressions.items():
            column = getattr(cls, col)
            operator, operand = list(expr.items())[0]
            operator = get_operator(operator)
            expression = operator(column, operand)
            filters.append(expression)
        return filters

    @classmethod
    def where(cls, state=None, archived=False, text=None, order_by=None, expressions=None):
        filters = []
        if state and state != "all":
            filters.append(cls.state == cls.STATE_LOOKUP[state])
        if archived is not None:
            filters.append(cls.archived == archived)
        if text:
            # import pdb; pdb.set_trace()
            filters += [match_text(cls, c, text[c]) for c in cls.TEXT_COLS if text.get(c)]
        if expressions:
            filters += cls.filter_expression(**expressions)

        ordering = cls.order_attr(order_by or {"date": "DESC"})
        return cls.query.filter(*filters).order_by(ordering())

    # onboard multiple remote petitions from the result of a query
    @classmethod
    def populate(cls, state="open", ids=None):
        logger.info("executing petition populate")
        discovered = ids or cls.discover(state=state)
        if not discovered:
            return discovered

        logger.info("fetching remote petitions")
        responses = cls.remote.async_get(petitions=discovered, max_retries=3)
        if not responses["success"]:
            raise RuntimeError(f"failed to fetch detailed remote data for IDs: {discovered}")

        populated, populated_ids = [], []
        logger.info("initializing local petitions")
        trend_index = cls.query.count() + len(responses["success"]) + 1
        for r in responses["success"]:
            petition = cls(id=r.data["data"]["id"], initial_data=r.data)
            petition.trend_index = trend_index
            petition.sync(r.data, r.timestamp)
            populated.append(petition)
            populated_ids.append(petition.id)

        logger.info("saving local petitions")
        db.session.bulk_save_objects(populated)
        db.session.commit()

        populated = list(cls.query.filter(cls.id.in_(populated_ids)).all())
        logger.info(f"populate completed, IDs: {populated_ids}")
        return populated

    # find remote petitions that have yet to be onboarded
    @classmethod
    def discover(cls, state="open"):
        logger.info("executing petition discovery")
        query = cls.remote.async_query(state=state, max_retries=3)
        if not any(query["success"]):
            raise RuntimeError(f"query response empty, failed indexes: '{len(query['failed'])}'")

        logger.info("comparing queried IDs against existing IDs")
        query = cls.remote.unpack_query(query)
        queried = {item["id"] for item in query}
        existing = {p[0] for p in cls.query.with_entities(Petition.id).all()}
        discovered = (queried - existing)

        logger.info(f"{len(discovered)} petitions discovered, IDs: {discovered}")
        return discovered

    # poll all petitions which match where param and kwargs opts (or provide list)
    # signatures_by = True for full geo records, signatures_by = False for basic total records
    @classmethod
    def poll(cls, geographic=False, petitions=None, where=None, min_growth=0, max_retries=3):
        logger.info("executing petition poll")
        petitions = petitions or cls.where(state="open", expressions=where).all()
        logger.info(f"polling petitions: {petitions}")
        if not petitions:
            return []

        responses = cls.remote.async_get(petitions=petitions, max_retries=max_retries)
        logger.info(f"petitions returned from async poll: {len(responses['success'])} ")
        if not responses["success"]:
            raise RuntimeError(f"no poll responses, failures: {len(responses['failed'])}")

        polled = [r.petition.sync(r.data, r.timestamp) for r in responses["success"]]
        db.session.flush()
        return cls.save_poll_data(polled, geographic, min_growth)

    @classmethod
    def save_poll_data(cls, petitions, geographic, min_growth):
        logger.info("executing save poll data")
        recorded = cls.save_base_data(petitions)
        if geographic:
            recorded = cls.save_geo_data(recorded, min_growth)

        logger.info("commiting poll!")
        db.session.commit()
        logger.info("completed poll!")
        return recorded

    # save basic record without detailed geographic signatures
    @classmethod
    def save_base_data(cls, petitions):
        logger.info("executing save base data")
        record_values = [Record.get_insert_map(p) for p in petitions]

        logger.info("bulk saving base records!")
        statement = postgresql.insert(Record).values(record_values).returning(Record.id)
        inserted = db.session.execute(statement).fetchall()
        db.session.flush()

        records = Record.query.filter(Record.id.in_([id[0] for id in inserted])).all()
        logger.info(f"base records saved: {len(records)}")
        return records

    # upgrade basic record to detailed geographic signatures record
    @classmethod
    def save_geo_data(cls, records, min_growth=0):
        logger.info("executing save geo data")
        signatures_by = []
        for r in records:
            signatures_by += r.build(r.petition.latest_data["data"]["attributes"])

        logger.info("bulk saving geo records")
        db.session.bulk_save_objects(signatures_by)
        db.session.flush()

        logger.info(f"geo records saved {len(records)}")
        return records

    @classmethod
    def update_trend_indexes(cls, since={"hours": 1}, margin={"minutes": 5}, handle_missing="reindex"):
        logger.info("updating petition trend indexes")
        found_petitions = cls.update_growth_rates(since, margin)
        found_ids = [p.id for p in found_petitions]

        missing_query = cls.where(state="open", archived=False).filter(cls.id.notin_(found_ids))
        missing_petitions = missing_query.order_by(Petition.growth_rate.desc()).all()
        missing_ids = [p.id for p in missing_petitions]

        petitions = cls.handle_trending_query(found_petitions, missing_petitions, handle_missing)
        logger.info("updating trend index")
        for index, petition in enumerate(petitions):
            petition.trend_index = index + 1

        db.session.commit()
        logger.info("succesfully updated trend indexes")
        return {"found": found_petitions, "missing": missing_petitions}

    @classmethod
    def handle_trending_query(cls, found, missing, action):
        sort_growth = lambda items: sorted(items, key=lambda p: p.growth_rate, reverse=True)
        if not missing:
            return sort_growth(found)

        if action == "concat":
            return sort_growth(found) + sort_growth(missing)
        if action == "reindex":
            return sort_growth(found + missing)
        else:
            raise PetitionsNotFound("trend index update", missing=missing, found=found)

    @classmethod
    def update_growth_rates(cls, since, margin):
        logger.info(f"updating petition growth rates since: {since}, margin: {margin}")

        since = dt.now() - timedelta(**since)
        margin = timedelta(**margin)
        timestamp = {"lt": since + margin, "gt": since - margin}
        distinct_opts = {"state": "open", "archived": False, "geographic": False}
        distinct_records = Record.distinct_on(timestamp=timestamp, opts=distinct_opts, order_by="DESC")
        if not distinct_records:
            raise RecordsNotFound("growth rate update", found=[])

        petitions = []
        logger.info("comparing petition growth rates")
        for record in distinct_records:
            record.petition.growth_rate = record.avg_growth_since()
            petitions.append(record.petition)

        db.session.commit()
        return petitions

    # sync remote petition data with petition columns and updated latest_data
    def sync(self, data, timestamp):
        self.polled_at = timestamp
        self.latest_data = deepcopy(data)
        self.archived = data["data"]["type"] == "archived-petition"
        self.url = self.remote.url_addr(self.id, self.archived)

        attributes = data["data"]["attributes"]
        self.pt_created_at = attributes.pop("created_at")
        self.pt_closed_at = attributes.pop("closed_at")
        self.pt_updated_at = attributes.pop("updated_at")
        self.pt_rejected_at = attributes.pop("rejected_at")
        self.signatures = attributes.pop("signature_count")
        self.state = attributes.pop("state")
        self.update(**attributes)
        return self

    def record_query(self, timestamp=None, geographic=None, filter_on=None, join_on=None, order="DESC"):
        filter_on = filter_on or {}
        timestamp = timestamp or {}
        filters = []

        if geographic is not None:
            filters.append(Record.geographic == geographic)
        if timestamp.get("lt"):
            filters.append(Record.timestamp <  self.lazy_strptime(timestamp["lt"]))
        if timestamp.get("gt"):
            filters.append(Record.timestamp > self.lazy_strptime(timestamp["gt"]))
        if filter_on.get("geography") and filter_on.get("locale"):
            geography, locale = filter_on["geography"], filter_on["locale"]
            filters.append(Record.get_locale_filter(geography, locale))

        query = self.records.filter(*filters)
        if join_on:
            query = query.options(joinedload(Record.relation_for(join_on)))

        ordering = getattr(Record.timestamp, order.lower())
        return query.order_by(ordering())

    def populate_self(self):
        return self.populate(ids=[self.id])

    def poll_self(self, geographic=True):
        return self.poll(petitions=[self.id], geographic=geographic)

    def fetch_self(self, raise_404=True):
        return self.remote.get(id=self.id, raise_404=raise_404)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self



class Record(db.Model):
    __tablename__ = "record"

    signatures_relation_attributes = {"back_populates": "record", "cascade": "all,delete-orphan"}
    signatures_query_attributes = {"passive_deletes": True, "lazy": "dynamic", **signatures_relation_attributes}
    signatures_select_attributes = {"lazy": "select", **signatures_relation_attributes}

    id = db.Column(Integer, primary_key=True)
    petition_id = db.Column(Integer, ForeignKey(Petition.id, ondelete="CASCADE"), index=True, nullable=False)
    timestamp = db.Column(DateTime, index=True, nullable=False)
    db_created_at = db.Column(DateTime, default=sqlfunc.now(), nullable=False)
    signatures = db.Column(Integer, nullable=False)
    geographic = db.Column(Boolean, default=False)
    petition = relationship(Petition, back_populates="records")
    signatures_by_country = relationship(lambda: SignaturesByCountry, **signatures_select_attributes)
    signatures_by_region = relationship(lambda: SignaturesByRegion, **signatures_select_attributes)
    signatures_by_constituency = relationship(lambda: SignaturesByConstituency, **signatures_select_attributes)

    country_query = relationship(lambda: SignaturesByCountry, **signatures_query_attributes)
    region_query = relationship(lambda: SignaturesByRegion,  **signatures_query_attributes)
    constiuency_query = relationship(lambda: SignaturesByConstituency, **signatures_query_attributes)
    ts = synonym("timestamp")

    def __repr__(self):
        template = "<record_id: {}, petition_id: {}, timestamp: {}, signatures: {}>"
        return template.format(self.id, self.petition_id, self.timestamp, self.signatures)

    @classmethod
    def validate_locale_choice(cls, inst, key, value):
        try:
            dict(inst.__class__.CODE_CHOICES)[value]
        except KeyError:
            value = inst.__class__.CODE_LOOKUP[value]
        return value

    @classmethod
    def code_for(cls, geo):
        return "code" if geo == "country" else "ons_code"

    @classmethod
    def model_for(cls, geo):
        return getattr(sys.modules[__name__], ("SignaturesBy" + geo.capitalize()))

    @classmethod
    def relation_for(cls, geo):
        return getattr(cls, cls.model_for(geo).__tablename__)

    @classmethod
    def table_for(cls, geo):
        return cls.model_for(geo).__table__

    @classmethod
    def locale_choice(cls, geography, k_or_v):
        if type(k_or_v) is dict:
            if k_or_v["code"] and k_or_v["value"]:
                return k_or_v

        model = cls.model_for(geography)
        choices = dict(model.CODE_CHOICES)
        try:
            choices[k_or_v.upper()]
            code = k_or_v.upper()
        except KeyError:
            code = model.CODE_LOOKUP[k_or_v]

        return {"code": code, "value": choices[code]}

    @classmethod
    def get_insert_map(cls, petition):
        return {
            "petition_id": petition.id,
            "signatures": petition.signatures,
            "timestamp": petition.polled_at,
            "db_created_at": sqlfunc.now()
        }

    @classmethod
    def get_locale_filter(cls, geography, locale):
        locale = cls.locale_choice(geography, locale) if type(locale) is str else locale
        equals_locale = cls.model_for(geography).code == locale["code"]
        return cls.relation_for(geography).any(equals_locale)

    @classmethod
    def signatures_query(cls, records, geography, locale, order=None):
        model = cls.model_for(geography)
        locale = cls.locale_choice(geography, locale)
        query = model.query.filter(Record.id.in_([r.id for r in records]))
        query = query.filter(model.code == locale["code"])
        ordering = getattr(Record.timestamp, (order or "DESC").lower())
        return query.join(cls).order_by(ordering())

    # query for a single (distinct) record for each petition
    @classmethod
    def distinct_on(cls, petitions=None, timestamp=None, filters=None, opts=None, order_by="DESC"):
        timestamp, filters, opts = timestamp or {}, filters or [], opts or {}

        filters.append(Petition.archived == opts.get("archived", False))
        if petitions:
            petition_ids = [p.id if type(p) is Petition else p for p in petitions]
            filters.append(Record.petition_id.in_(petition_ids))
        if opts.get("geographic") is not None:
            filters.append(Record.geographic == opts["geographic"])
        if opts.get("state"):
            filters.append(Petition.state == Petition.STATE_LOOKUP[opts["state"]])
        if timestamp.get("lt"):
            filters.append(Record.timestamp < timestamp["lt"])
        if timestamp.get("gt"):
            filters.append(Record.timestamp > timestamp["gt"])

        distinct_on, order_on = Record.petition_id, Record.timestamp
        ordering = [distinct_on, getattr(order_on, order_by.lower())()]

        query = Record.query.join(Petition)
        query = query.filter(*filters)
        query = query.order_by(*ordering)
        query = query.distinct(distinct_on)
        return query.all()

    def build(self, attributes):
        filter_attrs = lambda d, p: {k.replace(p, ""): v for k, v in d.items() if k.startswith(p)}
        geographies = filter_attrs(attributes, "signatures_by_")

        if not geographies:
            raise ValueError(f"no geography keys found for attributes: {attributes}")

        built = []
        for geo, locations in list(geographies.items()):
            model, code_key = Record.model_for(geo), self.code_for(geo)
            params = lambda x: {"code": x[code_key], "count": x["signature_count"]}
            built += [model(record_id=self.id, **params(locale)) for locale in locations]

        self.geographic = True
        return built

    def avg_growth_since(self):
        growth = (self.petition.signatures - self.signatures)
        period = (self.petition.polled_at - self.timestamp).total_seconds()
        return round(growth / (period / 60.0), 3)

    def query_by(self, geo):
        return getattr(self, f"{geo}_query")

    def signatures_by(self, geo):
        return getattr(self, f"signatures_by_{geo}")


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

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"), index=True, nullable=False)
    iso_code = db.Column(ChoiceType(CODE_CHOICES), index=True, nullable=False)
    count = db.Column(Integer, default=0)
    record = relationship(Record, back_populates="signatures_by_country")
    code = synonym("iso_code")

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates("iso_code")
    def validate_code_choice(self, key, value):
        return Record.validate_locale_choice(self, key, value)

    def __repr__(self):
        template = "<id: {}, code: {}, count: {}>"
        return template.format(self.id, self.code.code, self.count)



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

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"), index=True, nullable=False)
    ons_code = db.Column(ChoiceType(CODE_CHOICES), index=True, nullable=False)
    count = db.Column(Integer, default=0)
    record = relationship(Record, back_populates="signatures_by_region")
    code = synonym("ons_code")

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates("ons_code")
    def validate_code_choice(self, key, value):
        return Record.validate_locale_choice(self, key, value)

    def __repr__(self):
        template = "<id: {}, code: {}, count: {}>"
        return template.format(self.id, self.code.code, self.count)



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

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id, ondelete="CASCADE"), index=True, nullable=False)
    ons_code = db.Column(ChoiceType(CODE_CHOICES), index=True,  nullable=False)
    count = db.Column(Integer, default=0)
    record = relationship(Record, back_populates="signatures_by_constituency")
    code = synonym("ons_code")

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates("ons_code")
    def validate_code_choice(self, key, value):
        return Record.validate_locale_choice(self, key, value)

    def __repr__(self):
        template = "<id: {}, code: {}, count: {}>"
        return template.format(self.id, self.code.code, self.count)




# model serialization schemas
class SignaturesBySchema(SQLAlchemyAutoSchema):
    class Meta:
        include_relationships = True
        exclude = ["id"]

    def format_timestamp(self, obj):
        return obj.timestamp.strftime("%d-%m-%YT%H:%M:%S") if obj else None

    def get_code_field(self, obj):
        return obj.code.code if obj else None

    def get_name_field(self, obj):
        return obj.code.value if obj else None

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
        exclude = ["db_created_at", "geographic", "signatures"]

    @classmethod
    def schema_for(cls, geography):
        schema_name = f"SignaturesBy{geography.capitalize()}Schema"
        return getattr(sys.modules[__name__], schema_name)

    @classmethod
    def dump_query(cls, result, geography, locale=None, exclude=None):
        schemas = {}
        many, exclude = bool(not locale), (exclude or []) + [geography]
        schemas["signature"] = cls.schema_for(geography)(many=many, exclude=exclude)
        schemas["record"] = RecordSchema(exclude=["id"])

        kwargs = {"geography": geography, "locale": locale, "schemas": schemas}
        if isinstance(result, Iterable):
            return [cls.dump_query_item(result=r, **kwargs) for r in result]
        else:
            return cls.dump_query_item(result=result, **kwargs)

    @classmethod
    def dump_query_item(cls, result, geography, locale, schemas):
        if locale:
            signature = result
            record = result.record
        else:
            signature = result.signatures_by(geography)
            record = result

        geo_key = f"signatures_by_{geography}"
        dumped_signature = schemas["signature"].dump(signature)
        dumped_record = schemas["record"].dump(record)
        dumped_record[geo_key] = dumped_signature
        return dumped_record

    def signatures_by(self, geo):
        return getattr(self, "signatures_by_" + geo)

    def format_timestamp(self, obj):
        return obj.timestamp.strftime("%d-%m-%YT%H:%M:%S") if obj else None

    def rename_sig_key(self, obj):
        return obj.signatures if obj else None

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

    total = ma_fields.Method("rename_sig_key")
    signatures_by_country = Nested(SignaturesByCountrySchema, many=True, exclude=["country"])
    signatures_by_region = Nested(SignaturesByRegionSchema, many=True, exclude=["region"])
    signatures_by_constituency = Nested(SignaturesByConstituencySchema, many=True, exclude=["constituency"])



class PetitionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Petition
        exclude = ["initial_data", "latest_data", "db_updated_at"]

class PetitionNestedSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Petition
        include_relationships = True

    records = Nested(RecordSchema, many=True)
