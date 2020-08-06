import sqlalchemy
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, Integer, Boolean, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy_utils import *
from marshmallow_sqlalchemy import SQLAlchemySchema, SQLAlchemyAutoSchema, auto_field
from marshmallow_sqlalchemy.fields import Nested
from marshmallow import fields as ma_fields


import datetime
import enum
import sys
import requests
import json

from requests.exceptions import HTTPError
from requests.structures import CaseInsensitiveDict

from application import db
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

    # query helper method, will be expanded upon as project progresses
    # returns a query object if dynamic == True
    @classmethod
    def get(cls, **kwargs):
        filters = {}
        if kwargs.get('state'):
            filters['state'] = cls.STATE_LOOKUP[kwargs['state']]
        if kwargs.get('id'):
            filters['id'] = kwargs['id']
        
        query = cls.query.filter_by(**filters)
        if kwargs.get('limit'):
            query = query.limit(kwargs['limit'])
        if kwargs.get('dynamic', False):
            return query
        else:
            return query.all()

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

        params = cls.remote.deserialize(remote.data)
        petition = Petition(**params)
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
    
        for response in responses:
            print("creating record for ID: {}".format(response.petition_id))
            response.petition.archived = True if (response.data['data']['type'] == 'archived-petition') else False
            record = response.petition.create_record(
                attributes=response.data['data']['attributes'],
                timestamp = response.timestamp,
                commit=True
            )
            response.petition.records.append(record)
            records.append(record)
        
        db.session.commit()
        return records


    # poll the remote petition and return a deserialised object (optional commit)
    def poll(self, commit=True):
        remote = Petition.remote.get(self.id, raise_404=True)
        self.archived = True if (remote.data['data']['type'] == 'archived-petition') else False

        return self.create_record(
            attributes=remote.data['data']["attributes"],
            timestamp=remote.timestamp,
            commit=commit    
        )

    # create a new record for the petition from attributres json (optional commit)
    def create_record(self, attributes, timestamp, commit=True):
        record = Record.create(self.id, attributes, timestamp, commit=False)
        self.latest_data = attributes

        if commit: 
            db.session.commit()
        
        return record

    def __repr__(self):
        template = 'id: {}, url: {}, created_at: {}'
        return template.format(self.id, self.signatures, self.db_created_at)

    def __str__(self):
        template = 'petiton id: {}, action: {}'
        return template.format(self.id, self.action)

    def ordered_records(self, order="DESC"):
        if order == "DESC":
            return self.records.order_by(Record.timestamp.desc())
        if order == "ASC":
            return self.records.order_by(Record.timestamp)
        
        raise ValueError("Invalid order param, Must be 'DESC' or 'ASC'")
    
    def latest_record(self):
        return self.ordered_records().first()

class Record(db.Model):
    __tablename__ = 'record'

    id = db.Column(Integer, primary_key=True)
    petition_id = db.Column(Integer, ForeignKey(Petition.id), nullable=False)
    petition = relationship(Petition, back_populates="records")
    signatures_by_country = relationship("SignaturesByCountry", lazy='dynamic', back_populates="record", cascade="all,delete")
    signatures_by_region = relationship("SignaturesByRegion", lazy='dynamic', back_populates="record", cascade="all,delete")
    signatures_by_constituency = relationship("SignaturesByConstituency", lazy='dynamic', back_populates="record", cascade="all,delete")
    timestamp = db.Column(DateTime(timezone=True), nullable=False)
    db_created_at = db.Column(DateTime(timezone=True), default=sqlfunc.now(), nullable=False)
    signatures = db.Column(Integer, nullable=False)

    def __repr__(self):
        template = 'record_id: {}, petition_id: {}, timestamp: {}'
        return template.format(self.id, self.petition_id, self.timestamp)

    def __str__(self):
        template = 'Total signatures for petition id: {}, at {} - {}'
        return template.format(self.petition_id, self.timestamp, self.signatures)


    # short hand query helper query for signature geography + code or name
    def signatures_by(self, geography, value):
        table, model = self.get_sig_model_attr(geography)
        choices = dict(model.CODE_CHOICES)
        try:
            choices[value]
        except KeyError:
            value = model.CODE_LOOKUP[value]

        # *** needs a test added, might throw exception if no geography for that record ***
        return table.filter(model.code == value).one()

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
            for geography in list(signatures.keys()):
                table, model = record.get_sig_model_attr(geography)
                code = 'code' if geography == 'country' else 'ons_code'
                for locale in signatures[geography]:
                    table.append(model(code=locale[code], count=locale["signature_count"]))
            
        if commit: db.session.commit()
        
        return record

    # get signature models attr for a geography
    # to do: clean this up in an init or class var
    def get_sig_model_attr(self, geography):
        model = getattr(sys.modules[__name__], ('SignaturesBy' + geography.capitalize()))
        table = getattr(self, model.__tablename__)
        return table, model



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



# model serialisation schemas
class SignaturesBySchema(SQLAlchemyAutoSchema):
    class Meta:
        include_relationships = True
        load_instance = True

    @classmethod
    def get_schema_for(cls, model):
        return getattr(sys.modules[__name__], (model.__name__ + 'Schema'))

    def get_code_field(self, obj):
        return obj.code.code


    code = ma_fields.Method("get_code_field")

class SignaturesByConstituencySchema(SignaturesBySchema):
    class Meta(SignaturesBySchema.Meta):
        model = SignaturesByConstituency
        exclude = ("ons_code",)
    constituency = auto_field("ons_code", dump_only=True)

class SignaturesByCountrySchema(SignaturesBySchema):
    class Meta(SignaturesBySchema.Meta):
        model = SignaturesByCountry
        exclude = ("iso_code",)
    country = auto_field("iso_code", dump_only=True)

class SignaturesByRegionSchema(SignaturesBySchema):
    class Meta(SignaturesBySchema.Meta):
        model = SignaturesByRegion
        exclude = ("ons_code",)
    region = auto_field("ons_code", dump_only=True)

class RecordSchema(SQLAlchemySchema):
    class Meta:
        model = Record
        fields = ('id','petition_id', 'timestamp', 'signatures') 

class RecordNestedSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Record
        include_relationships = True
        load_instance = True
        exclude = ['db_created_at']
    
    signatures_by_country = Nested(SignaturesByCountrySchema, many=True)
    signatures_by_region = Nested(SignaturesByRegionSchema, many=True)
    signatures_by_constituency = Nested(SignaturesByConstituencySchema, many=True)

class PetitionSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Petition
        load_instance = True
        exclude = ['initial_data', 'latest_data']

class PetitionNestedSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Petition
        include_relationships = True
        load_instance = True

    records = Nested(RecordSchema, many=True)