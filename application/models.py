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
from application import db
from application.decorators import will_save_log

from requests.structures import CaseInsensitiveDict as LazyDict
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
    enabled = db.Column(Boolean, default=True, nullable=False)
    run_on_startup = db.Column(Boolean, default=False, nullable=False)
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
        return cls.query.filter_by(name=name.lower()).first()
    
    @classmethod
    def get_or_create(cls, name, **kwargs):
        return cls.get(name) or cls.create(name=name, **kwargs)
    
    @classmethod
    def get_interval(cls, task_name):
        return cls.get(task_name).interval

    @classmethod
    def create(cls, name, **kwargs):
        task = Task(name=name.lower(), **kwargs)
        db.session.add(task)
        db.session.commit()
        return task

    @classmethod
    def init_tasks(cls, config):
        tasks = [Task.create_or_update(**item) for item in config]
        db.session.add_all(tasks)
        db.session.commit()
        return tasks

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

    # kills unfinished runs in celery and sets them to failed (all)
    @classmethod
    def purge_all(cls, tasks=[]):
        tasks_to_purge = tasks or Task.query.all()
        return [task.clear_runs() for task in tasks_to_purge]

    # kills unfinished runs in celery and sets them to failed (instance)
    def purge(self):
        runs_to_purge = self.runs.filter(TaskRun.state.in_(["0","1","5"])).all()
        return [run.timeout() for run in runs_to_purge]
    
    # None periodic run from template
    def run(self, *args, **kwargs):
        return current_app.celery_utils.run_task(self.name, *args, **kwargs)

    def get_last(self, state="COMPLETED"):
        state = TaskRun.STATE_LOOKUP[state]
        query = self.runs.filter_by(state=state)
        query = query.order_by(TaskRun.finished_at.desc())
        return query.first()

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    # create new task run or initialize retrying task run
    def init_run(self, bind):
        kwargs = bind.request.kwargs
        worker_name = "{}_worker".format(kwargs["queue"])
        is_periodic = kwargs.get('periodic', False)

        if bind.request.retries > 0:
            task_run = TaskRun.query.get(kwargs["task_run_id"])
        else:
            task_run = TaskRun(state="PENDING", periodic=is_periodic, args=str(kwargs))
            self.runs.append(task_run)

        task_run.bind = bind
        task_run.celery_id = bind.request.id
        db.session.commit()
        task_run.init_logger(worker_name.upper())
        
        return task_run

    def clear_logs(self):
        logs = self.logs.all()
        for l in logs: db.session.delete(l)
        db.session.commit()
        return logs

    # return False if any TaskRuns with state in: [PENDING, RETRYING, RUNNING]
    # return True if last_run is None
    # return True if interval greater than time since last run
    def is_overdue(self):
        running_or_retrying = self.runs.filter(TaskRun.state.in_(["1","5"]))
        pending = self.runs.filter_by(state="0")

        if any(running_or_retrying.all()) or len(pending.all()) > 1:
            return False
        if not self.last_run:
            return True
        else:
            interval = datetime.timedelta(seconds=self.interval)
            elapsed = dt.now() - self.last_run
            return elapsed >= interval



class TaskRun(db.Model):

    STATE_CHOICES = [
        ('0', 'PENDING'),
        ('1', 'RUNNING'),
        ('2', 'COMPLETED'),
        ('3', 'FAILED'),
        ('4', 'REJECTED'),
        ('5', 'RETRYING')
    ]

    STATE_LOOKUP = LazyDict({v: k for k, v in dict(STATE_CHOICES).items()})

    id = db.Column(Integer, primary_key=True)
    celery_id = db.Column(String, nullable=False)
    task_id = db.Column(Integer, ForeignKey(Task.id), index=True, nullable=False)
    task = relationship(Task, back_populates="runs")
    logs = relationship(lambda: TaskLog, lazy='dynamic', back_populates="run", cascade="all, delete")
    state = db.Column(ChoiceType(STATE_CHOICES), nullable=False)
    periodic = db.Column(Boolean, default=False)
    retries = db.Column(Integer, default=0)
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
    
    def __repr__(self):
        template = '<id: {}, task_name: {}, state: {}>'
        return template.format(self.id, self.task.name, self.state.value)

    def timeout(self):
        self.init_logger()
        self.revoke()
        self.fail("manual timeout", reraise=False)
        self.finish()
        db.session.commit()

        return self

    def execute(self, func, *args, **kwargs):
        try:
            self.start()
            result = func(self, *args, **kwargs)
            self.complete()
        except Exception as error:
            if self.retries == self.max_retries:
                self.fail(error)
            else:
                self.retry(error)
        finally:
            self.finish()
        
        return result

    def init_logger(self, worker="default"):
        self.logger = Logger(
            model='task',
            worker=worker,
            module='handler',
            task_id=self.task_id,
            task_run_id=self.id
        )
    
    def is_overdue(self):
        if self.task.is_overdue(): 
            self.logger.info("{} - (OVERDUE [LAST RUN: {}])".format(self.task.name, self.task.last_run))
            return True
        else:
            return False
    
    def start(self):
        self.state = "RUNNING"
        self.started_at = dt.now()
        self.retries = self.bind.request.retries
        self.max_retries = self.bind.max_retries
        self.logger.info("{} - (RUNNING)".format(self.task.name))
        db.session.commit()

    def reject(self):
        self.state = "REJECTED"
        self.finished_at = datetime.datetime.now()
        self.logger.info("{} - (REJECTED)".format(self.task.name))
        db.session.commit()

    def skip(self):
        self.reject()
        self.logger.info("{} - (SKIPPING)".format(self.task.name))
        db.session.commit()

    def fail(self, error, reraise=True):
        if self.periodic:
            self.task.last_failed = dt.now()
        self.state = "FAILED"
        self.logger.error("{} - (FAILED) - ERROR: '{}'".format(self.task.name, error))
        db.session.commit()

        if reraise: raise

    def revoke(self):
        template = "{}  - (REVOKED [run_id: {}/cel_id: {}])"
        self.logger.info(template.format(self.task.name, self.id, self.celery_id))
        current_app.celery.control.revoke(self.celery_id)

    def retry(self, error):
        self.state = "RETRYING"
        countdown = (3 * self.retries + 1)
        msg = "{} - (RETRYING - [{}/{}] - [COUNTDOWN: {}]) - ERROR: {}"
        self.logger.error(
            msg.format(self.task.name, (self.retries + 1), self.bind.max_retries, countdown, error)
        )
        db.session.commit()

        self.bind.request.kwargs.update({"task_run_id": self.id})
        self.bind.retry(countdown=countdown)

    def complete(self):
        if self.periodic:
            self.task.last_run = self.started_at
        self.state = "COMPLETED"
        self.logger.info("{} - (COMPLETED)".format(self.task.name))
        db.session.commit()

    def finish(self):
        self.finished_at = dt.now()
        self.started_at = self.started_at or self.finished_at
        self.execution_time = (self.finished_at - self.started_at).total_seconds()
        template = "{} - (FINISHED/{} - [EXECUTION TIME: {}])"
        self.logger.info(template.format(self.task.name, self.state.value, self.execution_time))
        db.session.commit()

    def is_retrying(self):
        return self.state.value == "RETRYING"

    def print(self):
        for l in self.logs.all(): print(l)



class BaseLog(db.Model):
    LEVELS = [
        ('0', 'DEBUG'),
        ('1', 'INFO'),
        ('2', 'WARN'),
        ('3', 'ERROR'),
        ('4', 'FATAL')
    ]

    LEVEL_LOOKUP = LazyDict({v: k for k, v in dict(LEVELS).items()})

    __abstract__ = True
    level = db.Column(ChoiceType(LEVELS), nullable=False)
    timestamp = db.Column(DateTime, default=sqlfunc.now())
    module = db.Column(String)
    worker = db.Column(String)
    message = db.Column(String)

    # manual work around for broken choice validation in sqlalchemy utils
    @validates('level')
    def validate_level_choice(self, key, level):
        try:
            level = BaseLog.LEVEL_LOOKUP[level]
        except KeyError:
            dict(BaseLog.LEVELS)[level]

        return level

    def __repr__(self):
        template = '<id: {}, level: {}, timestamp: {}>'
        return template.format(self.id, self.level, self.timestamp)

    def __str__(self):
        template = '{} {} [{}]: {}'
        return template.format(self.timestamp, self.level.value, self.module, self.message)

    @classmethod
    def print(cls):
        for l in cls.query.all(): print(l)

    @classmethod
    def clear(cls, before=datetime.datetime.now()):
        logs = cls.query.filter(cls.timestamp < before).all()
        for l in logs: db.session.delete(l)
        db.session.commit()
        print("logs cleared: {}".format(len(logs)))


class TaskLog(BaseLog):
    __tablename__ = 'task_log'
    id = db.Column(Integer, primary_key=True)
    task_id = db.Column(Integer, ForeignKey(Task.id), index=True, nullable=False)
    task_run_id = db.Column(Integer, ForeignKey(TaskRun.id), index=True, nullable=False)
    task = relationship(Task, back_populates="logs")
    run = relationship(TaskRun, back_populates="logs")


    def __repr__(self):
        template = '<id: {}, level: {}, task: {}, timestamp: {}>'
        return template.format(self.id, self.level, self.task.name, self.timestamp)

    def __str__(self):
        template = '{} {} [{}][{}]: {}'
        return template.format(self.timestamp, self.level.value, self.module, self.task.name, self.message)

class AppLog(BaseLog):
    __tablename__ = 'app_log'
    id = db.Column(Integer, primary_key=True)



class Logger():

    LEVELS = BaseLog.LEVEL_LOOKUP
    MODELS = {'app': AppLog, 'task': TaskLog}

    def __init__(self, model, worker="FLASK", module=__name__, **kwargs):
        self.Model =  Logger.MODELS[model]
        self.kwargs = kwargs
        self.kwargs['worker'] = worker
        self.kwargs['module'] = module

    def __getattr__(self, f_name):
        def _missing(*args, **kwargs):
            level = f_name.upper()
            if level in Logger.LEVELS.keys():
                return self.log(level=level, *args, **kwargs)
        return _missing

    @will_save_log
    def log(self, msg, level="INFO", save=True):
        self.py_log(msg, level)
        if save: self.db_log(msg, level)

    def py_log(self, msg, level="DEBUG"):
        module, worker = self.kwargs['module'], self.kwargs['worker']
        msg = "[{}] [{}] {} ".format(worker, module, msg)
        logger = logging.getLogger(module)
        getattr(logger, level.lower())(msg)

    def db_log(self, msg, level="INFO"):
        log = self.Model(message=msg, level=level, **self.kwargs)
        db.session.add(log)
        db.session.commit()
    
    def func_log(self, name, level="INFO", **kwargs):
        msg = "executing function: '{}', kwargs: {}".format(name, kwargs)
        self.log(msg=msg, level=level)
