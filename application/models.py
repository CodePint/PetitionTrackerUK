import sqlalchemy
from sqlalchemy_utils import *
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy import (
    and_,
    inspect,
    Integer,
    Boolean,
    String,
    ForeignKey,
    DateTime,
    UniqueConstraint
)

from flask import current_app
from celery.utils.log import get_task_logger
from requests.structures import CaseInsensitiveDict as LazyDict
from application import db
from datetime import datetime as dt
import datetime
import logging

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
    def get(cls, key, type=str, default=None):
        setting = cls.query.filter_by(key=key).first()
        return type(setting.value) if setting else default

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



class Task(db.Model):
    id = db.Column(Integer, primary_key=True)
    runs = relationship(lambda: TaskRun, lazy='dynamic', back_populates="task")
    logs = relationship(lambda: TaskLog, lazy='dynamic', back_populates="task")
    name = db.Column(String, nullable=False, unique=True)
    enabled =  db.Column(Boolean, default=True, nullable=False)
    interval = db.Column(Integer)
    last_run = db.Column(DateTime)
    last_failed = db.Column(DateTime)
    db_created_at = db.Column(DateTime, default=sqlfunc.now())
    db_updated_at = db.Column(DateTime, default=sqlfunc.now(), onupdate=sqlfunc.now())

    def __repr__(self):
        template = '<id: {}, name: {}, enabled: {}, last_run: {}>'
        return template.format(self.id, self.name, self.enabled, self.last_run)

    @classmethod
    def get(cls, name):
        return cls.query.filter_by(name=name).first()
    
    @classmethod
    def get_or_create(cls, name, **kwargs):
        return cls.get(name) or cls.create(name=name, **kwargs)
    
    @classmethod
    def get_interval(cls, task_name):
        return cls.get(task_name).interval

    @classmethod
    def create(cls, name, with_run=False, **kwargs):
        task = Task(name=name, **kwargs)
        db.session.add(task)
        db.session.commit()
        return task

    @classmethod
    def init_tasks(cls, config):
        tasks = [Task.create_or_update(**item) for item in config]
        db.session.add_all(tasks)
        db.session.commit()

    @classmethod
    def create_or_update(cls, name, **kwargs):
        task = cls.get(name)
        if not task:
            return cls.create(name, **kwargs)
        else:
            task.update(**kwargs)
            db.session.commit()
            return task

    @classmethod
    def run_task(cls, name):
        current_app.celery_utils.run_task(name)

    @classmethod
    def get_last_run(cls, name, before=None):
        task = Task.get(name)
        query = task.runs.filter_by(state="COMPLETE")
        if before:
            lt = dt.now() - datetime.timedelta(**before)
            query = query.filter(TaskRun.finished_at < lt)
        
        return query.order_by(TaskRun.finished_at.desc()).first()
    
    def run(self, *args, **kwargs):
        return current_app.celery_utils.run_task(self.name)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def init_run(self, task_args='', **kwargs):
        task_run = TaskRun(state="PENDING", **kwargs)
        task_run.args = str(task_args)
        self.runs.append(task_run)
        db.session.commit()

        return task_run

    def clear_logs(self):
        logs = self.logs.all()
        for l in logs: db.session.delete(l)
        db.session.commit()

        return logs

    # return true if last_run is None or if interval greater than time since last run
    def is_overdue(self):
        now = datetime.datetime.now()
        interval = datetime.timedelta(seconds=self.interval)
        return bool(not self.last_run or ((now - self.last_run) >= interval))


class TaskRun(db.Model):

    STATE_CHOICES = [
        ('0', 'PENDING'),
        ('1', 'RUNNING'),
        ('2', 'COMPLETED'),
        ('3', 'FAILED'),
        ('4', 'REJECTED'),
    ]

    STATE_LOOKUP = LazyDict({v: k for k, v in dict(STATE_CHOICES).items()})

    id = db.Column(Integer, primary_key=True)
    task_id = db.Column(Integer, ForeignKey(Task.id), index=True, nullable=False)
    task = relationship(Task, back_populates="runs")
    logs = relationship(lambda: TaskLog, back_populates="run", cascade="all, delete")
    state = db.Column(ChoiceType(STATE_CHOICES), nullable=False)
    args = db.Column(String)
    started_at = db.Column(DateTime)
    finished_at = db.Column(DateTime)
    execution_time = db.Column(Integer)
    db_created_at = db.Column(DateTime, default=sqlfunc.now())
    db_updated_at = db.Column(DateTime, default=sqlfunc.now(), onupdate=sqlfunc.now())

    # manual work around for broken choice validation in sqlalchemy utils
    @validates('state')
    def validate_state_choice(self, key, state):
        try:
            state = TaskRun.STATE_LOOKUP[state]
        except KeyError:
            dict(TaskRun.STATE_CHOICES)[state]

        return state
    
    def is_successful(self):
        return self.state.value == "COMPLETED" and self.state.finished_at
    
    def is_failed(self):
        return self.state.value == "FAILED"

    def reject(self):
        self.state = "REJECTED"
        self.finished_at = datetime.datetime.now()
        db.session.commit()


class BaseLog(db.Model):

    LEVELS = [
        ('I', 'INFO'),
        ('D', 'DEBUG'),
        ('W', 'WARN'),
        ('E', 'ERROR'),
        ('F', 'FATAL')
    ]

    LEVEL_LOOKUP = LazyDict({v: k for k, v in dict(LEVELS).items()})

    id = db.Column(Integer, primary_key=True)
    level = db.Column(ChoiceType(LEVELS), nullable=False)
    timestamp = db.Column(DateTime, default=sqlfunc.now())
    message = db.Column(String)

    # manual work around for broken choice validation in sqlalchemy utils
    @validates('level')
    def validate_level_choice(self, key, level):
        try:
            level = TaskLog.LEVEL_LOOKUP[level]
        except KeyError:
            dict(TaskLog.LEVELS)[level]

        return level

class TaskLog(BaseLog):
    task_id = db.Column(Integer, ForeignKey(Task.id), index=True, nullable=False)
    task_run_id = db.Column(Integer, ForeignKey(TaskRun.id), index=True, nullable=False)
    task = relationship(Task, back_populates="logs")
    run = relationship(TaskRun, back_populates="logs")

class AppLog(BaseLog):
    app = db.Column(String, index=True, nullable=False)
    module = db.Column(String, index=True, nullable=False)


class Logger:

    LEVELS = ('DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL')

    def __init__(self, source, app_name='FLASK'):
        self.source = source
        self.app_name = app_name
        self.base_logger = logging.getLogger(source)

    def __getattr__(self, f_name):
        def _missing(*args, **kwargs):
            level = f_name.upper()
            if level in Logger.LEVELS:
                return self.log(level=level, *args, **kwargs)
        return _missing

    def log(self, msg, level="INFO"):
        getattr(self.base_logger, level)(msg)

class TaskLogger(Logger):

    def __init__(self, task_run, worker):
        self.task_run = task_run
        self.worker = worker
        base_logger = get_task_logger(worker)

    def log(self, msg, level="INFO"):
        super().log(msg, level)
        log = TaskLog(message=msg, level=level, task_id=self.task.id)
        self.task_run.logs.append(log)
        db.session.commit()
        return log


class AppLogger(Logger):

    def log(self, msg, level="INFO"):
        super().log(msg, level)
        log = AppLog(message=msg, level=level, app=self.app_name, module=self.source)
        db.session.add(log)
        db.session.commit()
        return log