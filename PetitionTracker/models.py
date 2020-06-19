import sqlalchemy

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy_utils import *

import datetime
import enum

db = SQLAlchemy()

class StateChoices(enum.Enum):

    def __str__(self):
        return self.name

    open = 0
    closed = 1
    rejected = 2

class Petition(db.Model):
    __tablename__ = "petition"

    STATES = [
        ('O', 'Open'),
        ('C', 'Closed'),
        ('R', 'Rejected')
    ]

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


class Record(db.Model):
    __tablename__ = 'record'
    id = db.Column(Integer, primary_key=True)
    petition_id = db.Column(Integer, ForeignKey(Petition.id), nullable=False)
    petition = relationship(Petition, back_populates="records")
    signatures_by_country = relationship("SignaturesByCountry", back_populates="record")
    signatures_by_region = relationship("SignaturesByRegion", back_populates="record")
    signatures_by_constituency = relationship("SignaturesByConstituency", back_populates="record")
    timestamp = db.Column(DateTime(timezone=True), default=sqlfunc.now())
    signatures = db.Column(Integer)

class SignaturesByCountry(db.Model):
    __tablename__ = 'signatures_by_country'

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_country")
    iso_code = db.Column(String(3))
    count = db.Column(Integer)

class SignaturesByRegion(db.Model):
    __tablename__ = 'signatures_by_region'

    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_region")
    ons_code = db.Column(String(3))
    count = db.Column(Integer)

class SignaturesByConstituency(db.Model):

    __tablename__ = 'signatures_by_constituency'
    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_constituency")
    ons_code = db.Column(String(9))
    count = db.Column(Integer)

# Petition.query.get(12345).records.order_by("timestamp").all()