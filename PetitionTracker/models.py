import sqlalchemy

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy_utils import *

import datetime

db = SQLAlchemy()

class Petition(db.Model):

    STATES = [
        (0, 'Open'),
        (1, 'Closed'),
        (2, 'Rejected')
    ]

    __tablename__ = "petition"
    id = db.Column(Integer, primary_key=True, autoincrement=False)
    state = db.Column(ChoiceType(STATES), nullable=False)
    records = relationship(lambda: Record, back_populates="petition")
    action = db.Column(String(512), index=True, unique=True)
    signatures = db.Column(Integer)
    url = db.Column(String(2048), index=True, unique=True)
    background: db.Column(String)
    additional_details: db.Column(String)
    pt_created_at = db.Column(DateTime)
    pt_updated_at = db.Column(DateTime)
    pt_rejected_at = db.Column(DateTime)
    db_created_at = db.Column(DateTime(timezone=True), default=sqlfunc.now())
    db_updated_at = db.Column(DateTime(timezone=True), onupdate=sqlfunc.now())
    initial_json = db.Column(JSONType)
    latest_json = db.Column(JSONType)

    def __repr__(self):
        return '<petition id: {}, action: {} >'.format(self.id, self.action)

    def __str__(self):
        return self.action


class Record(db.Model):
    __tablename__ = 'record'
    id = db.Column(Integer, primary_key=True)
    timestamp = db.Column(DateTime(timezone=True), default=sqlfunc.now())
    petition_id = db.Column(Integer, ForeignKey(Petition.id))
    petition = relationship(Petition, back_populates="records")
    total_signatures = relationship("TotalSignatures", back_populates="record")
    signatures_by_country = relationship("SignaturesByCountry", back_populates="record")
    signatures_by_region = relationship("SignaturesByRegion", back_populates="record")
    signatures_by_constituency = relationship("SignaturesByConstituency", back_populates="record")

class SignaturesByCountry(db.Model):
    __tablename__ = 'signatures_by_country'
    id = db.Column(Integer, primary_key=True)
    record_id = db.Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_country")
    iso_code = db.Column(String(3))
    count = db.Column(Integer)


class TotalSignatures(db.Model):
    __tablename__ = 'total_signatures'
    id = db.Column(Integer, primary_key=True)
    record_id = db.Column("Record.records", ForeignKey(Record.id))
    record = relationship(Record, back_populates="total_signatures")
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

