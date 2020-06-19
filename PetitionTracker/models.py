import sqlalchemy
import sqlalchemy_utils
import datetime

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy_utils import ChoiceType, JSONType

from sqlalchemy.ext.declarative import declarative_base
BASE = declarative_base()

from .app import db

class Petition(BASE):

    STATES = [
        (0, 'Open'),
        (1, 'Closed'),
        (2, 'Rejected')
    ]

    __tablename__ = "petition"
    id = Column(Integer, primary_key=True, autoincrement=False)
    records = relationship(lambda: Record, back_populates="petition")
    state = Column(ChoiceType(STATES))
    action = Column(String(512), index=True, unique=True)
    signatures = Column(Integer)
    url = Column(String(2048), index=True, unique=True)
    background: Column(String)
    additional_details: Column(String)
    pt_created_at = Column(DateTime)
    pt_updated_at = Column(DateTime)
    pt_rejected_at = Column(DateTime)
    db_created_at = Column(DateTime(timezone=True), default=sqlfunc.now())
    db_updated_at = Column(DateTime(timezone=True), onupdate=sqlfunc.now())
    initial_json = Column(JSONType)
    latest_json = Column(JSONType)

    def __repr__(self):
        return '<petition id: {}, action: {} >'.format(self.id, self.action)

    def __str__(self):
        return self.action


class Record(BASE):
    __tablename__ = 'record'
    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime(timezone=True), default=sqlfunc.now())
    petition_id = Column(Integer, ForeignKey(Petition.id))
    petition = relationship(Petition, back_populates="records")
    total_signatures = relationship("TotalSignatures", back_populates="record")
    signatures_by_country = relationship("SignaturesByCountry", back_populates="record")
    signatures_by_region = relationship("SignaturesByRegion", back_populates="record")
    signatures_by_constituency = relationship("SignaturesByConstituency", back_populates="record")

class SignaturesByCountry(BASE):
    __tablename__ = 'signatures_by_country'
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_country")
    iso_code = Column(String(3))
    count = Column(Integer)


class TotalSignatures(BASE):
    __tablename__ = 'total_signatures'
    id = Column(Integer, primary_key=True)
    record_id = Column("Record.records", ForeignKey(Record.id))
    record = relationship(Record, back_populates="total_signatures")
    count = Column(Integer)

class SignaturesByRegion(BASE):
    __tablename__ = 'signatures_by_region'
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_region")
    ons_code = Column(String(3))
    count = Column(Integer)

class SignaturesByConstituency(BASE):
    __tablename__ = 'signatures_by_constituency'
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey(Record.id))
    record = relationship(Record, back_populates="signatures_by_constituency")
    ons_code = Column(String(9))
    count = Column(Integer)

