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
from application.tracker.remote import RemotePetition
from application.tracker.geographies.choices.regions import REGIONS
from application.tracker.geographies.choices.countries import COUNTRIES
from application.tracker.geographies.choices.constituencies import CONSTITUENCIES
from application.tracker.exceptions import PetitionsNotFound, RecordsNotFound

from math import ceil, floor
from datetime import datetime as dt
from datetime import timedelta
import operator as operators
import datetime, operator, json, sys, logging

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
    record_rel_attrs = {"lazy": "dynamic", "back_populates": "petition", "cascade": "all,delete-orphan"}
    records = relationship(lambda: Record, **record_rel_attrs)

    # handles requests for petition data scraping
    remote = RemotePetition

    def __repr__(self):
        template = "<id: {}, signatures: {}, created_at: {}>"
        return template.format(self.id, self.signatures, self.db_created_at)

    # work around for broken choice validation in sqlalchemy utils
    # also allows case agnostic value/key of the state tuple
    @validates("state")
    def validate_state_choice(self, key, state):
        try:
            state = self.STATE_LOOKUP[state]
        except KeyError:
            dict(self.STATE_CHOICES)[state]
        return state

    @classmethod
    def str_or_datetime(cls, time):
        return dt.strptime(time, "%d-%m-%YT%H:%M:%S") if type(time) is str else time

    @classmethod
    def get_ids(cls, petitions):
        return [p.id for p in petitions]

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

        populated = cls.query.filter(cls.id.in_(populated_ids)).all()
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
    def poll(cls, petitions=None, query=None, geographic=False, min_growth=0, **filters):
        logger.info("executing petition poll")
        petitions = petitions or cls.query_expr(query=query, **filters).all()
        logger.info(f"Petitions returned from query: {len(petitions)}")
        if not petitions:
            return []

        responses = cls.remote.async_get(petitions=petitions, max_retries=3)
        logger.info(f"petitions returned from async poll: {len(responses['success'])} ")
        if not any(responses["success"]):
            raise RuntimeError(f"no poll responses, failures: {len(responses['failed'])}")

        polled = [r.petition.sync(r.data, r.timestamp) for r in responses["success"]]
        db.session.flush()
        return cls.save_poll_data(polled, geographic, min_growth)

    # expressions: {"signatures": {"gt": 10_000}, "trend_index": {"le": 10} }
    @classmethod
    def query_expr(cls, state="open", archived=False, query=None, **expressions):
        query = query or cls.query.filter_by(state=cls.STATE_LOOKUP[state], archived=archived)
        compare = lambda col, opr, opd: getattr(operators, opr)(getattr(cls, col), opd)
        for column, expr in expressions.items():
            operator, operand = list(expr.items())[0]
            query = query.filter(compare(column, operator, operand))
        return query

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
        found_ids = cls.get_ids(found_petitions)

        missing_filters = [cls.state == "O", cls.archived == False, cls.id.notin_(found_ids)]
        missing_petitions = cls.query.filter(*missing_filters).order_by(Petition.growth_rate.desc()).all()
        missing_ids = cls.get_ids(missing_petitions)

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

        if action is "concat":
            return sort_growth(found) + sort_growth(missing)
        if action is "reindex":
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
        attributes = data["data"]["attributes"]
        self.polled_at = timestamp
        self.url = data["links"]["self"]
        self.archived = data["data"]["type"] == "archived-petition"
        self.pt_created_at = attributes["created_at"]
        self.pt_closed_at = attributes["closed_at"]
        self.pt_updated_at = attributes["updated_at"]
        self.pt_rejected_at = attributes["rejected_at"]
        self.signatures = attributes["signature_count"]
        self.state = attributes["state"]
        self.latest_data = data
        self.update(**attributes)
        return self

    def populate_self(self):
        return self.populate(ids=[self.id])

    def poll_self(self, commit=True, geo=True):
        return self.poll(petitions=[self.id], commit=commit, geo=geo)

    def fetch_self(self, raise_404=True):
        return self.remote.get(id=self.id, raise_404=raise_404)

    # To Do: merge closest, between, since and ordered
    def get_closest_record(self, to, geographic=True):
        query = self.records.filter_by(geographic=geographic)
        query = query.filter(Record.timestamp < self.str_or_datetime(to))
        return query.order_by(Record.timestamp.desc()).first()

    # returns a query objects for all records between timedelta
    def query_records_between(self, lt, gt, geographic=True):
        lt, gt = self.str_or_datetime(lt), self.str_or_datetime(gt)
        query = self.records.filter_by(geographic=geographic)
        query = query.filter(Record.timestamp > gt).filter(and_(Record.timestamp < lt))
        return query.order_by(Record.timestamp.desc())

    # returns a query objects for all records since timedelta
    def query_records_since(self, since, now=None, geographic=True):
        now = self.str_or_datetime(now) if now else dt.now()
        query = self.records.filter(Record.timestamp > (now - timedelta(**since)))
        query = query.filter_by(geographic=geographic)
        return query.order_by(Record.timestamp.desc())

    # returns a query object for the petitions records
    def ordered_records(self, order="DESC", geographic=None):
        ordering = getattr(Record.timestamp, order.lower())
        query = self.records.order_by(ordering())
        if geographic is not None:
            query = query.filter_by(geographic=geographic)

        return query

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

    def signatures_by(self, geo):
        return getattr(self, "signatures_by_" + geo)

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
    def table_for(cls, geo):
        return cls.model_for(geo).__table__

    @classmethod
    def atrributes_for(cls, geo):
        model = cls.model_for(geo)
        return {
            "model": model,
            "table": model.__table__,
            "name": model.__tablename__,
            "relationship": getattr(cls,  model.__tablename__),
            "schema_class": SignaturesBySchema.schema_for(geo)
        }

    @classmethod
    def locale_choice(cls, geography, key_or_value):
        model = cls.model_for(geography)
        choices = dict(model.CODE_CHOICES)
        try:
            choices[key_or_value.upper()]
            code = key_or_value.upper()
        except KeyError:
            code = model.CODE_LOOKUP[key_or_value]

        return {"code": code, "value": choices[code]}

    @classmethod
    def attributes_map(cls, *geographies):
        return {geo: cls.atrributes_for(geo) for geo in geographies}

    @classmethod
    def get_insert_map(cls, petition):
        return {
            "petition_id": petition.id,
            "signatures": petition.signatures,
            "timestamp": petition.polled_at,
            "db_created_at": sqlfunc.now()
        }

    # query for a single (distinct) record for each petition
    @classmethod
    def distinct_on(cls, timestamp=None, petitions=None, filters=None, opts=None, order_by="DESC"):
        timestamp, filters, opts = timestamp or {}, filters or [], opts or {}

        filters.append(Petition.archived == opts.get("archived", False))
        if opts.get("geographic") is not None:
            filters.append(Record.geographic == opts["geographic"])
        if opts.get("state"):
            filters.append(Petition.state == Petition.STATE_LOOKUP[opts["state"]])
        if petitions:
            petition_ids = [p.id if type(p) is Petition else p for p in petitions]
            filters.append(Record.petition_id.in_(petition_ids))
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

    # @classmethod
    # def filter_min_growth(cls, records, threshold, geographic=True):
    #     petitions = [r.petition_id for r in records]
    #     query = Record.distinct_on(petitions=petitions, geographic=geographic)
    #     previous = query.order_by(Record.petition_id.desc())
    #     current = sorted(records, key=lambda r: r.petition_id)

    #     filter_growth = lambda prev, curr: (curr.signatures - prev.signatures) >= threshold
    #     return [curr for prev, curr in zip(previous, current) if filter_growth(prev, curr)]

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

    # helper query for signature geography + code or name
    def signatures_for(self, geo, locale):
        model = Record.model_for(geo)
        choice = Record.locale_choice(geo, locale)
        query = self.signatures_by(geo).filter(model.code == choice["code"])
        try:
            return query.one()
        except sqlalchemy.orm.exc.NoResultFound:
            return None

    def signatures_comparison(self, record_schema, attrs):
        comparison = record_schema.dump(self)
        for geo in attrs.keys():
            relation = self.signatures_by(geo)
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

    def __repr__(self):
        template = "<id: {}, code: {}, count: {}>"
        return template.format(self.id, self.code.code, self.count)




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
