import sqlalchemy
from sqlalchemy_utils import *
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy import and_, tuple_, event
from sqlalchemy import inspect as sqlinspect
from sqlalchemy import (
    Integer,
    Boolean,
    String,
    ForeignKey,
    DateTime,
    UniqueConstraint
)
from marshmallow_sqlalchemy.fields import Nested
from marshmallow_sqlalchemy import SQLAlchemySchema, SQLAlchemyAutoSchema
from flask import current_app as c_app
from application import db

from requests.structures import CaseInsensitiveDict as LazyDict
from contextlib import contextmanager
from celery_once import helpers as CeleryOnceUtils
from datetime import datetime as dt
from datetime import timedelta
from time import sleep
import datetime, math, time, json, inspect, logging

logger = logging.getLogger(__name__)

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



class Event(db.Model):
    id = db.Column(Integer, primary_key=True)
    name = db.Column(String, index=True, nullable=False)
    msg = db.Column(String, default="N/A")
    ts = db.Column(DateTime, index=True, nullable=False, default=sqlfunc.now())

    def __str__(self):
        return f"name: {self.name}, timestamp: {self.timestamp}"

    def __repr__(self):
        return f"name: {self.name}, msg: {self.msg}, ts: {self.ts}"

    @classmethod
    def called(cls, name, order="desc"):
        return Event.query.filter_by(name=name).order_by(getattr(Event.ts, order)())

    @classmethod
    def first(cls, name):
        return Event.called(name=name, order="asc").first()

    @classmethod
    def last(cls, name):
        return Event.called(name=name, order="desc").first()

    # max range expects timedelta
    @classmethod
    def closest(cls, name, ts, max_range=None):
        query = Event.query.filter_by(name=name)
        gt_event = query.filter(Event.ts > ts).order_by(Event.ts.asc()).first()
        lt_event = query.filter(Event.ts < ts).order_by(Event.ts.desc()).first()
        if not gt_event and not lt_event:
            logger.info(f"no events exist with name '{name}'")
            return None

        gt_diff = (gt_event.ts - ts).total_seconds() if gt_event else math.inf
        lt_diff  = (ts - lt_event.ts).total_seconds() if lt_event else math.inf
        max_range = timedelta(**max_range).total_seconds() if max_range else None
        out_of_range = max_range and (gt_diff > max_range) and (lt_diff > max_range)

        if out_of_range:
            logger.info(f"no events with: '{name}', within range")
        else:
            return gt_event if gt_diff < lt_diff else lt_event



class TaskNotFound(NameError):
    def __init__(self, name, key):
        self.message = f"No task found with name: {name}, key: {key}"

class Task(db.Model):

    __table_args__ = (
        db.UniqueConstraint(
            "name", "key",
            name="uniq_name_key_for_task"),
    )

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String, nullable=False)
    key = db.Column(String, nullable=False)
    module = db.Column(String, nullable=False)
    enabled = db.Column(Boolean, default=False)
    startup = db.Column(Boolean, default=False)
    periodic = db.Column(Boolean, default=False)
    description = db.Column(String)
    kwargs = db.Column(JSONType)
    opts = db.Column(JSONType)
    schedule = db.Column(JSONType)
    last_failed = db.Column(DateTime)
    last_success = db.Column(DateTime)
    db_created_at = db.Column(DateTime, default=sqlfunc.now())
    db_updated_at = db.Column(DateTime, default=sqlfunc.now(), onupdate=sqlfunc.now())
    runs_rel_attrs = {"lazy": "dynamic", "back_populates": "task", "cascade": "all,delete-orphan"}
    runs = relationship(lambda: TaskRun, **runs_rel_attrs)

    def __repr__(self):
        return f"<id: {self.id}, name: {self.name}, key: {self.key}, enabled: {self.enabled}>"

    @classmethod
    def get(cls, name, key, enabled=None, will_raise=False):
        task = cls.query.filter_by(name=name.lower(), key=key).first()
        if not task and will_raise:
            raise TaskNotFound(name, key)

        if task and enabled and task.enabled is not enabled:
            logger.info(f"Task disabled {name}/{key}")
            return None

        return task

    @classmethod
    def parse_config(cls, **config):
        timeout = config["opts"].get("once", {}).get("timeout")
        if timeout:
            timeout = round(timedelta(**timeout).total_seconds())
            config["opts"]["once"]["timeout"] = timeout

        config["opts"]["queue"] = config["module"]
        config["kwargs"]["key"] = config["key"]
        config["kwargs"]["periodic"] = config["periodic"]
        return config

    @classmethod
    def get_all(cls, tasks):
        task_tuples = [tuple(t.values()) for t in tasks]
        tuple_filter = sqlalchemy.tuple_(Task.name, Task.key).in_(task_tuples)
        return Task.query.filter(tuple_filter).all()

    @classmethod
    def get_or_create(cls, **config):
        config = cls.parse_config(**config)
        task = Task.get(name=config["name"], key=config["key"])
        if not task:
            task = Task(**config)
            db.session.add(task)
            db.session.commit()

        return task

    @classmethod
    def create_or_update(cls, **config):
        config = cls.parse_config(**config)
        task = Task.get(name=config["name"], key=config["key"])
        task = task.update(**config) if task else Task(**config)
        db.session.add(task)
        db.session.commit()

        return task

    @classmethod
    def purge_locks(cls, pattern="qo_*"):
        lock_keys = cls.get_lock_keys(pattern)
        if lock_keys:
            logger.info(f"deleting lock keys: {lock_keys}")
            c_app.redis.delete(*lock_keys)

        return lock_keys

    @classmethod
    def get_lock_keys(cls, pattern="qo_*"):
        return c_app.redis.keys(pattern=pattern)

    @classmethod
    def revoke_all(cls, tasks=None):
        tasks_to_revoke = tasks or Task.query.all()
        return [task.revoke(["PENDING", "RUNNING", "RETRYING"]) for task in tasks_to_revoke]

    @property
    def once_opts(self):
        return self.opts.get("once", {})

    @property
    def is_retrying(self):
        return bool(self.where(["RETRYING"]).count())

    @property
    def is_pending(self):
        return bool(self.where(["PENDING"]).count())

    def revoke(self, *states):
        return [run.revoke() for run in self.where(states).all()]

    def unlock(self):
        return [run.unlock() for run in self.runs.all()]

    def run(self, kwargs=None):
        return c_app.celery_utils.send_task(task=self, **(kwargs or {}))

    def where(self, states, unique=False):
        states = [TaskRun.STATE_LOOKUP[s] for s in states]
        query = self.runs.filter(TaskRun.state.in_(states))
        return query.filter_by(unique=unique)

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self



class MissingTaskHandler(ValueError):
    def __init__(self, bind, run_id=None, msg="Handler ID empty"):
        self.message = f"No handler found for ID: {run_id}" if run_id else msg

class TaskRun(db.Model):

    STATE_CHOICES = [
        ("0", "PENDING"),
        ("1", "RUNNING"),
        ("2", "SUCCESSFUL"),
        ("3", "FAILED"),
        ("4", "REVOKED"),
        ("5", "RETRYING")
    ]

    STATE_LOOKUP = LazyDict({v: k for k, v in dict(STATE_CHOICES).items()})
    DEFAULT_LOCK_EXPIRY = lambda: c_app.config.get("CELERY_ONCE_DEFAULT_TIMEOUT")
    MAX_RETRY_COUNTDOWN =  lambda: c_app.config.get("CELERY_MAX_RETRY_COUNTDOWN")

    id = db.Column(Integer, primary_key=True)
    task_id = db.Column(Integer, ForeignKey(Task.id), index=True, nullable=False)
    task = relationship(Task, back_populates="runs")
    state = db.Column(ChoiceType(STATE_CHOICES), nullable=False)
    celery_id = db.Column(String)
    retries = db.Column(Integer, default=0)
    max_retries = db.Column(Integer, default=0)
    retries_countdown = db.Column(Integer)
    kwargs = db.Column(JSONType)
    started_at = db.Column(DateTime)
    finished_at = db.Column(DateTime)
    revoke_msg = db.Column(String)
    lock_key = db.Column(String)
    unique = db.Column(Boolean, default=False)
    error = db.Column(String)
    result = db.Column(JSONType)
    periodic = db.Column(Boolean, default=False)
    db_created_at = db.Column(DateTime, default=sqlfunc.now())
    db_updated_at = db.Column(DateTime, default=sqlfunc.now(), onupdate=sqlfunc.now())

    def __repr__(self):
        task = f"name: {self.task.name}, key: {self.task.key}"
        return f"<id: {self.id}, state: {self.state}, {task}>"

    # manual work around for broken choice validation in sqlalchemy utils
    @validates("state")
    def validate_state_choice(self, key, state):
        try:
            state = TaskRun.STATE_LOOKUP[state]
        except KeyError:
            dict(TaskRun.STATE_CHOICES)[state]

        return state

    @hybrid_property
    def run_time(self):
        running_time = lambda: (self.finished_at or dt.now()) - (self.started_at)
        return running_time() if self.started_at else timedelta(seconds=0)

    @classmethod
    def get_or_raise(cls, id, retry_race=False):
        task_run = cls.query.get(id)
        if task_run:
            return task_run
        if retry_race:
            sleep(3) or cls.get(id, retry_race=False)
        raise MissingTaskHandler(id)

    def getcallkwargs(self, func):
        signature = inspect.signature(func).parameters.values()
        parameters = [k.name for k in list(signature)]
        return {k: v for k, v in self.kwargs.items() if k in parameters}

    @classmethod
    def configure(cls, bind):
        run_id = bind.request.kwargs.get("id")
        handler = cls.get_or_raise(run_id, retry_race=True)
        handler.bind = bind
        if handler.state != "RETRYING":
            kwargs = handler.bind.request.kwargs
            handler.update(
                unique=kwargs.get("unique", False),
                periodic=kwargs.get("periodic", False),
                max_retries=handler.bind.max_retries,
                kwargs=kwargs,
            )
        handler.celery_id = handler.bind.request.id
        handler.retries = handler.bind.request.retries
        db.session.commit()
        logger.info(f"handler id: {run_id}, configured succesfully")

        return handler

    @classmethod
    @contextmanager
    def execute(cls, bind):
        handler = cls.configure(bind)
        try:
            handler.start()
            yield handler
            handler.succeed()
        except Exception as error:
            if handler.retries >= handler.max_retries:
                handler.fail(error)
                raise
            else:
                handler.retry(error)

    def start(self):
        self.started_at = self.started_at or dt.now()
        self.set("RUNNING")

    def succeed(self):
        self.finished_at = dt.now()
        if not self.unique:
            self.task.last_success = self.finished_at
        self.set("SUCCESSFUL")

    def fail(self, error):
        db.session.rollback()
        self.finished_at = dt.now()
        if not self.unique:
            self.task.last_failed = self.finished_at
        self.error = str(error)
        self.unlock()
        self.set("FAILED")

    def retry(self, error):
        db.session.rollback()
        self.error = str(error)
        self.set_countdown()
        self.set("RETRYING")
        self.bind.retry(countdown=self.retries_countdown)

    def revoke(self, reason=None):
        try:
            c_app.celery.control.revoke(self.celery_id)
            self.revoke_msg  = reason
            self.finished_at = dt.now()
            if not self.state in ["FAILED", "SUCCESSFUL"]:
                self.set("REVOKED")
        except Exception as error:
            logger.error(f"error: {error}, while revoking ID: {self.id}/{self.celery_id}")
            return False

        self.unlock()
        return self.id

    def commit(self, result, schema=None):
        try:
            result = schema.dump(result) if schema else json.dumps(result)
            logger.info(f"task result: {result}")
        except (TypeError, OverflowError) as e:
            result = str(result)
            logger.info(f"task result: {result}, marshal error: {e}")

        self.result = {"result": result}
        db.session.commit()
        return self.result

    def set(self, state):
        self.state = state
        db.session.commit()

        if not sqlinspect(self).transient and getattr(self, 'bind', None):
            self.bind.handler = TaskRunRelationalSchema().dump(self)

        base_msg = f"TASK {state} - RUN TIME: {round(self.run_time.total_seconds(), 3)}"
        if state == "RETRYING":
            retry_count = f"{(self.retries + 1)}/{self.max_retries}"
            logger.warn(f"{base_msg}: [{retry_count} - COUNTDOWN: {self.retries_countdown}s]")
        elif state == "REVOKED":
            logger.info(f"{base_msg}: [{self.celery_id}/{self.task.key} - {self.revoke_msg}]")
        elif state in ["SUCCESSFUL", "FAILED"]:
            logger.info(f"{base_msg}: RUN DETAILS, {self.bind.handler}")
        else:
            logger.info(base_msg)

    def set_countdown(self, exponent=3):
        maximum = self.kwargs.get("max_retry_countdown", TaskRun.MAX_RETRY_COUNTDOWN())
        countdown = (exponent ** (self.retries + 1))
        self.retries_countdown = countdown if countdown < maximum else maximum
        return self.retries_countdown

    def get_state(self):
        return dict(TaskRun.STATE_CHOICES)[self.state]

    def unlock(self):
        if self.lock_key:
            logger.info(f"releasing lock for run: {self}")
            c_app.redis.delete(self.lock_key)
        else:
            logger.warn(f"no lock key saved for run: {self}")
        return self

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        return self



class SettingSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Setting

class EventSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Event

class TaskSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Task

class TaskRunSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TaskRun
        include_relationships = False

class TaskRunRelationalSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = TaskRun
        include_relationships = False

    task = Nested(TaskSchema)

class TaskNestedSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = Task

    runs = Nested(TaskRunSchema)
