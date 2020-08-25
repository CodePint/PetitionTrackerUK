import sqlalchemy
from flask import abort, current_app
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, Integer, Boolean, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy_utils import *
from marshmallow_sqlalchemy import SQLAlchemySchema, SQLAlchemyAutoSchema, auto_field
from marshmallow_sqlalchemy.fields import Nested
from marshmallow import fields as ma_fields, pre_dump

import datetime as dt
import enum
import sys
import requests
import json

from requests.exceptions import HTTPError
from requests.structures import CaseInsensitiveDict

from application import db
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
    STATE_LOOKUP = CaseInsensitiveDict({v: k for k, v in dict(STATE_CHOICES).items()})

    id = db.Column(Integer, primary_key=True, autoincrement=False)
    state = db.Column(ChoiceType(STATE_CHOICES), nullable=False)
    archived = db.Column(Boolean, default=False, nullable=False)
    records = relationship(lambda: Record, lazy='dynamic', back_populates="petition", cascade="all,delete")
    action = db.Column(String(512), index=True, unique=True)
    url = db.Column(String(2048), index=True, unique=True)
    signatures = db.Column(Integer)
    background = db.Column(String)
    additional_details = db.Column(String)
    pt_created_at = db.Column(DateTime)
    pt_updated_at = db.Column(DateTime)
    pt_rejected_at = db.Column(DateTime)
    polled_at = db.Column(DateTime)
    db_created_at = db.Column(DateTime(timezone=True), default=sqlfunc.now())
    db_updated_at = db.Column(DateTime(timezone=True), default=sqlfunc.now(), onupdate=sqlfunc.now())
    initial_data = db.Column(JSONType)
    latest_data = db.Column(JSONType)
    
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
    
        # poll the remote petition and return a deserialised object (optional commit)
    def poll(self, commit=True):
        response = Petition.remote.get(self.id, raise_404=True)
        self.polled_at = response.timestamp
        self.update(response.data['data']["attributes"], response.timestamp)
        self.set_archive_state(response.data['data']['type'])
        
        print("creating record for petition ID: {}".format(self.id))
        return self.create_record(
            attributes=response.data['data']["attributes"],
            timestamp=response.timestamp,
            commit=commit    
        )

    # To Do: add these details to petition db model
    # --- "moderation_threshold_reached_at" (timestamp)
    # --- "response_threshold_reached_at" (timestamp)
    def update(self, attributes, timestamp):
        self.polled_at = timestamp
        self.signatures = attributes['signature_count']
        self.pt_updated_at = attributes['updated_at']
        self.pt_rejected_at = attributes['rejected_at']

    def set_archive_state(self, type):
        self.archived = True if (type == 'archived-petition') else False
        return self.archived

    # create a new record for the petition from attributres json (optional commit)
    def create_record(self, attributes, timestamp, commit=True):
        record = Record.create(self.id, attributes, timestamp, commit=False)
        self.latest_data = attributes

        if commit: 
            db.session.commit()
        
        return record

    # between ex: {'lt': dt(), 'gt': gt()}
    #### *** Need to test *** ###
    def query_records_between(self, lt, gt):
        return self.records.timestamp.between(lt, gt)

    # since ex: {'hours': 12}, {'days': 7}, {'month': 1}
    def query_records_since(self, since):
        ago = dt.datetime.now() - dt.timedelta(**since)
        query = self.records.filter(Record.timestamp > ago)
        return query.order_by(Record.timestamp.desc())

    def ordered_records(self, order="DESC"):
        if order == "DESC":
            return self.records.order_by(Record.timestamp.desc())
        if order == "ASC":
            return self.records.order_by(Record.timestamp)
        
        raise ValueError("Invalid order param, Must be 'DESC' or 'ASC'")
    
    def latest_record(self):
        return self.ordered_records().first()

    @classmethod
    def get_or_404(cls, id):
        petition = Petition.query.get(id)
        return petition or ViewUtils.json_abort(404, "Petition ID: {}, not found".format(id))

    # onboard multiple remote petitions from the result of query
    @classmethod
    def populate(cls, state, query=[], count=False, archived=False):
        query = cls.remote.query(count=count, query=query, state=state, archived=archived)
        ids = [item['id'] for item in query if not cls.query.get(item['id'])]
        result = cls.remote.async_get(ids, retries=3)
        remotes = result.get('success')

        populated = []
        for item in remotes:
            print("onboarding petition ID: {}".format(item.petition_id))
            petition = cls.onboard(remote=item, commit=False)
            db.session.add(petition)
            populated.append(petition)
        
        db.session.commit()
        return populated

    # onboard a remote petition by id (optional commit & attributes)
    @classmethod
    def onboard(cls, id=None, remote=None, commit=True):
        if not remote:
            remote = cls.remote.get(id, raise_404=True)
        attributes = remote.data['data']["attributes"]
        params = cls.remote.deserialize(remote.data)
        petition = Petition(**params)
        petition.update(attributes, remote.timestamp)
        record = petition.create_record(
            attributes=remote.data['data']["attributes"],
            timestamp=remote.timestamp,
            commit=False
        )

        if commit:
            db.session.add(record)
            db.session.add(petition)
            db.session.commit()
        else:
            petition.records.append(record)
        
        return petition

    @classmethod
    def poll_all(cls):
        petitions = cls.query.filter_by(state='O', archived=False).all()
        results = cls.remote.async_poll(petitions, retries=3)
        responses = results.get('success')
        records = []
    
        for resp in responses:
            petition = resp.petition
            attributes = resp.data['data']['attributes']            
            petition.set_archive_state(resp.data['data']['type'])
            petition.update(attributes, resp.timestamp)

            print("creating record for petition ID: {}".format(petition.id))
            record = petition.create_record(
                attributes=attributes,
                timestamp=resp.timestamp,
                commit=True
            )

            petition.records.append(record)
            records.append(record)
        
        db.session.commit()
        return records



class Record(db.Model):
    __tablename__ = 'record'

    id = db.Column(Integer, primary_key=True)
    petition_id = db.Column(Integer, ForeignKey(Petition.id), nullable=False)
    petition = relationship(Petition, back_populates="records")
    by_country = relationship("SignaturesByCountry", back_populates="record", cascade="all,delete")
    by_region = relationship("SignaturesByRegion", back_populates="record", cascade="all,delete")
    by_constituency = relationship("SignaturesByConstituency", back_populates="record", cascade="all,delete")
    signatures_by_country = relationship("SignaturesByCountry", lazy='dynamic', back_populates="record", cascade="all,delete")
    signatures_by_region = relationship("SignaturesByRegion", lazy='dynamic', back_populates="record", cascade="all,delete")
    signatures_by_constituency = relationship("SignaturesByConstituency", lazy='dynamic', back_populates="record", cascade="all,delete")
    timestamp = db.Column(DateTime(timezone=True), nullable=False)
    db_created_at = db.Column(DateTime(timezone=True), default=sqlfunc.now(), nullable=False)
    signatures = db.Column(Integer, nullable=False)

    def __repr__(self):
        template = '<record_id: {}, petition_id: {}, timestamp: {}>'
        return template.format(self.id, self.petition_id, self.timestamp)

    def __str__(self):
        template = 'Total signatures for petition id: {}, at {} - {}'
        return template.format(self.petition_id, self.timestamp, self.signatures)
    
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
            choices[key_or_value]
            code = key_or_value
        except KeyError:
            code = model.CODE_LOOKUP[key_or_value]
        
        value = choices[code]
        return {'code': code, 'value': value}
    
    # create a new record for the petition from attributres json (optional commit)
    @classmethod
    def create(cls, petition_id, attributes, timestamp, commit=True):
        signatures = {}
        signatures['country'] = attributes.get('signatures_by_country', None)
        signatures['constituency'] = attributes.get('signatures_by_constituency', None)
        signatures['region'] = attributes.get('signatures_by_region', None)

        record = Record(petition_id=petition_id)
        record.timestamp = timestamp
        record.signatures = attributes['signature_count']

        if any(signatures.values()):
            for geo in list(signatures.keys()):
                model = cls.get_sig_model(geo)
                relation = record.get_sig_relation(geo)
                code = 'code' if geo == 'country' else 'ons_code'
                for locale in signatures[geo]:
                    relation.append(model(code=locale[code], count=locale["signature_count"]))
            
        if commit: db.session.commit()
        
        return record
    
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
    CODE_LOOKUP = CaseInsensitiveDict({v: k for k, v in dict(CODE_CHOICES).items()})
    code = synonym("iso_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id), nullable=False)
    record = relationship(Record, back_populates="signatures_by_country")
    iso_code = db.Column(ChoiceType(CODE_CHOICES), nullable=False)
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
    CODE_LOOKUP = CaseInsensitiveDict({v: k for k, v in dict(CODE_CHOICES).items()})
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id), nullable=False)
    record = relationship(Record, back_populates="signatures_by_region")
    ons_code = db.Column(ChoiceType(CODE_CHOICES), nullable=False)
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
    CODE_LOOKUP = CaseInsensitiveDict({v: k for k, v in dict(CODE_CHOICES).items()})
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id), nullable=False)
    record = relationship(Record, back_populates="signatures_by_constituency")
    ons_code = db.Column(ChoiceType(CODE_CHOICES), nullable=False)
    count = db.Column(Integer, default=0)

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

    @validates('ons_code')
    def validate_code_choice(self, key, value):
        return ModelUtils.validate_geography_choice(self, key, value)
    
    def __str__(self):
        return '{} - {}'.format(self.code.value, self.count)


# model helper utils
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