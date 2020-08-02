import sqlalchemy
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import inspect, Integer, Boolean, String, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy_utils import *

from application import db

class Setting(db.Model):
    id = db.Column(Integer, primary_key=True)
    key = db.Column(String, index=True, unique=True)
    value = db.Column(String)
    meta = db.Column(String)

    def __repr__(self):
        return str({self.key: self.value})

    @classmethod
    def has(cls, key):
        return bool(cls.query.filter_by(key=key).first())

    @classmethod
    def get(cls, key):
        setting = cls.query.filter_by(key=key).first()
        if setting:
            return setting.value

    @classmethod
    def configure(cls, config):
        defaults = []
        for key, value in config.items():
            setting = cls.create_or_update(key=key, value=value)
            db.session.add(setting)
            defaults.append(setting)
        
        db.session.commit()
        return defaults

    @classmethod
    def create_or_update(cls, key, value):
        existing_setting = cls.query.filter_by(key=key).first()

        if not existing_setting:
            setting = cls(key=key, value=value)
            db.session.add(setting)
        else:
            setting = existing_setting
            setting.value = value
        
        db.session.commit()
        return setting
