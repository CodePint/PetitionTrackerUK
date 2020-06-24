import sqlalchemy

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy_utils import *

import datetime
import enum
import sys
import requests
import json

from PetitionTracker import db

class Petition(db.Model):
    __tablename__ = "petition"

    STATES = [
        ('C', 'Closed'),
        ('R', 'Rejected'),
        ('O', 'Open'),
        ('D', 'Debated'),
        ('ND', 'Not Debated'),
        ('AW', 'Awaiting Response'),
        ('WR', 'With Response'),
        ('AW', 'Awaiting Debate')
    ]

    BASE_URL = "https://petition.parliament.uk/petitions"

    id = db.Column(Integer, primary_key=True, autoincrement=False)
    state = db.Column(ChoiceType(STATES), nullable=False)
    records = relationship(lambda: Record, lazy='dynamic', back_populates="petition")
    action = db.Column(String(512), index=True, unique=True)
    signatures = db.Column(Integer)
    url = db.Column(String(2048), index=True, unique=True)
    background: db.Column(String)
    additional_details: db.Column(String)
    pt_created_at = db.Column(DateTime)
    pt_updated_at = db.Column(DateTime)
    pt_rejected_at = db.Column(DateTime)
    db_created_at = db.Column(DateTime(timezone=True), default=sqlfunc.now())
    db_updated_at = db.Column(DateTime(timezone=True), default=sqlfunc.now(), onupdate=sqlfunc.now())
    initial_json = db.Column(JSONType)
    latest_json = db.Column(JSONType)

    def __repr__(self):
        template = '<petition id: {}, action: {}, signatures: {}>'
        return template.format(self.id, self.action, self.signatures)

    def __str__(self):
        return self.action

    def ordered_records(self, order="DESC"):
        if order == "DESC":
            return self.records.order_by(Record.timestamp.desc())
        if order == "ASC":
            return self.records.order_by(Record.timestamp)
        
        raise ValueError("Invalid order param, Must be 'DESC' or 'ASC'")

    def last_record(self):
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

    def __init__(self):
        self.signature_relations = [rel.mapper.class_ for rel in inspect(Record)]

    def signatures_by(self, geography, code):
        table = getattr(self, ("signatures_by_" + geography ))
        model = getattr(sys.modules[__name__], ('SignaturesBy' + geography.capitalize()))
        return table.filter(model.code == code).one()


class SignaturesByCountry(db.Model):
    __tablename__ = 'signatures_by_country'
    code = synonym("iso_code")
    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_country")
    iso_code = db.Column(String(3))
    count = db.Column(Integer)

class SignaturesByRegion(db.Model):
    __tablename__ = 'signatures_by_region'
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_region")
    ons_code = db.Column(String(3))
    count = db.Column(Integer)

class SignaturesByConstituency(db.Model):
    __tablename__ = 'signatures_by_constituency'
    code = synonym("ons_code")

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_constituency")
    ons_code = db.Column(String(9))
    count = db.Column(Integer)

# Petition.query.get(12345).records.order_by("timestamp").all()

# get the latest record for a petition by timestamp
# Petition.query.get(12345).records.order_by(Record.timestamp.desc()).first()
# Petition.query.get("12345").ordered_records().first().signatures_by_region.filter(SignaturesByRegion.ons_code == "N").first()