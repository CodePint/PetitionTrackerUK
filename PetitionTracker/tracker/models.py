import sqlalchemy

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, Integer, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy_utils import *

import datetime
import enum
import sys
import requests
import json

from requests.exceptions import HTTPError
from .remote import RemotePetition
from PetitionTracker import db

class Petition(db.Model):
    __tablename__ = "petition"

    STATES = [
        ('C', 'closed'),
        ('R', 'rejected'),
        ('O', 'open'),
    ]

    id = db.Column(Integer, primary_key=True, autoincrement=False)
    state = db.Column(ChoiceType(STATES), nullable=False)
    records = relationship(lambda: Record, lazy='dynamic', back_populates="petition")
    action = db.Column(String(512), index=True, unique=True)
    signatures = db.Column(Integer)
    url = db.Column(String(2048), index=True, unique=True)
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
        state = state.lower()
        choices = dict(Petition.STATES)

        if state not in list(choices.keys()):
            choices = {v: k for k, v in choices.items()}
        
        return choices[state]

    # onboard multiple remote petitions from the result of query
    @classmethod
    def populate(cls, query=[], count=False, state='open'):
        results = cls.remote.query(count=count, query=query, state=state)

        populated = []
        for item in results:
            id = item['id']
            petition = cls.onboard(id=id, commit=False)
            populated.append(petition)
            db.session.add(petition)
        
        db.session.commit()
        return populated

    # onboard a remote petition by id (optional commit)
    @classmethod
    def onboard(cls, id, commit=True):
        response = cls.remote.get(id, raise_404=True).json()
        params = cls.remote.deserialize(response)
        petition = Petition(**params)
        record = petition.create_record(attributes=response['data']["attributes"], commit=False)
        petition.records.append(record)

        if commit:
            db.session.add(petition)
            db.session.commit()
        
        return petition

    # poll the remote petition and return a deserialised object (optional commit)
    def poll(self, commit):
        response = cls.remote.get(self.id, raise_404=True).json()
        attributes = response['data']["attributes"]
        return self.create_record(commit=commit, attributes=attributes)

    # create a new record for the petition from attributres json (optional commit)
    def create_record(self, attributes, commit=True):
        signatures = {}
        signatures['country'] = attributes.get('signatures_by_country', None)
        signatures['constituency'] = attributes.get('signatures_by_constituency', None)
        signatures['region'] = attributes.get('signatures_by_region', None)

        record = Record(petition_id=self)
        for geography in list(signatures.keys()):
            table, model = record.get_sig_model_attr(geography)
            code = 'code' if geography == 'country' else 'ons_code'
            for locale in signatures[geography]:
                table.append(model(code=locale[code], count=locale["signature_count"]))
        
        if commit:
            self.records.append(record)
            self.latest_data = response
            db.session.commit()
            
        return record

    def __repr__(self):
        template = '<petition id: {}, signatures: {}, action: {}>'
        return template.format(self.id, self.signatures, self.action)

    def __str__(self):
        return self.action

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
    signatures_by_country = relationship("SignaturesByCountry", lazy='dynamic', back_populates="record")
    signatures_by_region = relationship("SignaturesByRegion", lazy='dynamic', back_populates="record")
    signatures_by_constituency = relationship("SignaturesByConstituency", lazy='dynamic', back_populates="record")
    timestamp = db.Column(DateTime(timezone=True), default=sqlfunc.now())
    signatures = db.Column(Integer)

    # short hand query helper query for signature geography + code
    def signatures_by(self, geography, code):
        table, model = self.get_sig_model_attr(geography)
        return table.filter(model.code == code).one()

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
    code = synonym("iso_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_country")
    iso_code = db.Column(String(3))
    count = db.Column(Integer)

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp



class SignaturesByRegion(db.Model):
    __tablename__ = 'signatures_by_region'
    __table_args__ = (
        db.UniqueConstraint('record_id', 'ons_code', name="uniq_sig_region_for_record"),
    )
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_region")
    ons_code = db.Column(String(3))
    count = db.Column(Integer)

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp



class SignaturesByConstituency(db.Model):
    __tablename__ = 'signatures_by_constituency'
    __table_args__ = (
        db.UniqueConstraint('record_id', 'ons_code', name="uniq_sig_constituency_for_record"),
    )
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_constituency")
    ons_code = db.Column(String(9))
    count = db.Column(Integer)

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp