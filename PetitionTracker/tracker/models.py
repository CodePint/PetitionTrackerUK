import sqlalchemy

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy_utils import *

import datetime
import enum
import sys
import requests
import json

from requests.exceptions import HTTPError
from .remote import Remote
from PetitionTracker import db

class Petition(db.Model):
    __tablename__ = "petition"

    STATES = [
        ('C', 'Closed'),
        ('R', 'Rejected'),
        ('O', 'Open'),
    ]

    BASE_URL = "https://petition.parliament.uk/petitions"

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
    
    @classmethod
    def onboard(cls, id):
        response = Remote.fetch(id, raise_404=True).json()
        params = Remote.deserialize(response)
        petition = Petition(**params)
        db.session.add(petition)
        db.session.commit()

        return petition

    def poll(self, commit=True):
        response = Remote.fetch(self.id, raise_404=True).json()
        attributes = response['data']["attributes"]
        
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

    # manual work around for broken choice validation in sqlalchemy utils
    # also allows case agnostic value/key of the state tuple to be used as an argument
    @validates('state')
    def validate_state_choice(self, key, state):
        state = state.capitalize()
        choices = dict(Petition.STATES)

        if state not in list(choices.keys()):
            choices = {v: k for k, v in choices.items()}
        
        return choices[state]

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
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_constituency")
    ons_code = db.Column(String(9))
    count = db.Column(Integer)

    @reconstructor
    def init_on_load(self):
        self.timestamp = self.record.timestamp

# Petition.query.get(12345).records.order_by("timestamp").all()
# get the latest record for a petition by timestamp
# Petition.query.get("300412").records.order_by(Record.timestamp.desc()).first()
# Petition.query.get("300412").ordered_records().first().signatures_by_country.filter(SignaturesByCountry.code == "E").first()
# Petition.query.get("300412").add_record()
# record.signatures_by_country.append(SignaturesByCountry(code="E", count="500"))
# petition = Petition.query.get(300412)