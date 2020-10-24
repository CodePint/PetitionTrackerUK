import sqlalchemy
from sqlalchemy_utils import *
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import relationship, synonym, validates, reconstructor
from sqlalchemy.sql import functions as sqlfunc
from sqlalchemy import and_, tuple_, inspect, event
from sqlalchemy import (
    Integer,
    Boolean,
    String,
    ForeignKey,
    DateTime,
    UniqueConstraint
)

from flask import current_app
from application import db

from requests.structures import CaseInsensitiveDict as LazyDict
from datetime import datetime as dt
import datetime, time
import logging

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



class Task(db.Model):

    __table_args__ = (
        db.UniqueConstraint(
            "name", "key",
            name="uniq_name_key_for_task"),
    )

    id = db.Column(Integer, primary_key=True)
    name = db.Column(String, nullable=False)
    module = db.Column(String, nullable=False)
    key = db.Column(String, nullable=False)
    description = db.Column(String, nullable=False)
    enabled = db.Column(Boolean, default=False)
    startup = db.Column(Boolean, default=False)
    periodic = db.Column(Boolean, default=False)
    last_fail = db.Column(DateTime)
    last_success = db.Column(DateTime)
    options = db.Column(JSONType)
    kwargs = db.Column(JSONType)
    interval = db.Column(JSONType)
    db_created_at = db.Column(DateTime, default=sqlfunc.now())
    db_updated_at = db.Column(DateTime, default=sqlfunc.now(), onupdate=sqlfunc.now())
    runs_rel_attrs = {"lazy": "dynamic", "back_populates": "task", "cascade": "all,delete-orphan"}
    runs = relationship(lambda: TaskRun, **runs_rel_attrs)

    def __repr__(self):
        return f"<id: {self.id}, name: {self.name}, key: {self.key}, enabled: {self.enabled}>"

    @classmethod
    def get(cls, name, key, will_raise=False):
        task = cls.query.filter_by(name=name.lower(), key=key).first()
        if not task and will_raise:
            raise NameError(f"No task found with name: {name}, key: {key}")

        return task

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

        if task:
            task.update(**config)
        else:
            task = Task(**config)

        db.session.add(task)
        db.session.commit()
        return task

    @classmethod
    def parse_config(cls, **config):
        config["kwargs"]["singleton"] = config["run"].pop("singleton", False)
        config["kwargs"]["name"] = config["name"]
        config["kwargs"]["key"] = config["key"]
        config["options"]["queue"] = config["module"]
        config.update(config.pop("run"))

        return config

    @classmethod
    def get_interval(cls, task_name):
        return cls.get(task_name).interval

    @classmethod
    def run_task(cls, name):
        current_app.celery_utils.run_task(name)

    # purge all runs for all tasks for all states
    @classmethod
    def purge_all(cls, tasks=[]):
        tasks_to_purge = tasks or Task.query.all()
        return [task.purge_runs() for task in tasks_to_purge]

    # kills unfinished runs in celery and postgres for all states
    def purge_runs(self, runs=[]):
        run_to_purge = runs or self.runs.query.all()
        return [run.timeout() for run in run_to_purge]

    # purges runs with matching state and db_updated_at before updated
    def purge_runs_where(self, state, updated_lt=None, except_ids=None):
        updated_defaults = {"RETRYING": TaskRun.MAX_COUNTDOWN, "PENDING": 15, "RUNNING": self.interval}
        query = self.runs.filter_by(state=TaskRun.STATE_LOOKUP[state])

        if except_ids:
            query = query.filter(TaskRun.id.notin_(except_ids))
        if updated_lt:
            updated_lt = updated_lt or updated_defaults.get(state.upper(), 0)
            query = query.filter(TaskRun.db_updated_at < round(time.time() - updated_lt))

        runs_to_purge = query.all()
        purged = [run.timeout() for run in runs_to_purge]
        logger.debug(f"Purged {len(purged)} {state} runs. IDs: {purged}")

        return purged

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
        is_singleton = kwargs.get("singleton", False)

        if bind.request.retries > 0:
            task_run = TaskRun.query.get(kwargs["task_run_id"])
        else:
            task_run = TaskRun(state="PENDING", singleton=is_singleton, kwargs=kwargs)
            self.runs.append(task_run)

        task_run.bind = bind
        task_run.celery_id = bind.request.id
        db.session.commit()

        for state in ["RETRYING", "PENDING", "RUNNING"]:
            self.purge_runs_where(state, except_ids=[task_run.id])

        return task_run

    def any_active_runs(self, excluding_id):
        states = [TaskRun.STATE_LOOKUP[s] for s in ["PENDING", "RUNNING", "RETRYING",]]
        query = self.runs.filter(TaskRun.state.in_(states))
        if excluding_id:
            query = query.filter(TaskRun.id != excluding_id)

        return any(query.all())

    def is_overdue(self):
        if not self.last_success:
            return True

        interval = datetime.timedelta(seconds=self.interval)
        elapsed = dt.now() - self.last_success
        return elapsed >= interval



class TaskRun(db.Model):

    STATE_CHOICES = [
        ("0", "PENDING"),
        ("1", "RUNNING"),
        ("2", "SUCCESSFUL"),
        ("3", "FAILED"),
        ("4", "REJECTED"),
        ("5", "RETRYING")
    ]

    STATE_LOOKUP = LazyDict({v: k for k, v in dict(STATE_CHOICES).items()})
    MAX_COUNTDOWN = 300

    id = db.Column(Integer, primary_key=True)
    celery_id = db.Column(String, nullable=False)
    task_id = db.Column(Integer, ForeignKey(Task.id), index=True, nullable=False)
    task = relationship(Task, back_populates="runs")
    state = db.Column(ChoiceType(STATE_CHOICES), nullable=False)
    singleton = db.Column(Boolean, default=False)
    retries = db.Column(Integer, default=0)
    kwargs = db.Column(JSONType)
    started_at = db.Column(DateTime)
    finished_at = db.Column(DateTime)
    execution_time = db.Column(Integer)
    db_created_at = db.Column(DateTime, default=sqlfunc.now())
    db_updated_at = db.Column(DateTime, default=sqlfunc.now(), onupdate=sqlfunc.now())

    # manual work around for broken choice validation in sqlalchemy utils
    @validates("state")
    def validate_state_choice(self, key, state):
        try:
            state = TaskRun.STATE_LOOKUP[state]
        except KeyError:
            dict(TaskRun.STATE_CHOICES)[state]

        return state

    def __repr__(self):
        template = "<id: {}, task_name: {}, state: {}>"
        return template.format(self.id, self.task.name, self.state)

    def get_state(self):
        return dict(TaskRun.STATE_CHOICES)[self.state]

    def execute(self, func, *args, **kwargs):
        try:
            self.start()
            result = func(self, *args, **kwargs)
            self.complete()
        except Exception as error:
            if self.retries >= self.max_retries:
                self.fail(error)
                raise
            else:
                self.retry(error)
        finally:
            self.finish()

        return result

    def will_run(self):
        if self.singleton:
            if self.task.any_active_runs(excluding_id=self.id):
                return False
            if self.task.periodic:
                return self.task.is_overdue()
        else:
            return True

    def timeout(self):
        self.revoke()

        if not self.state in ["FAILED", "SUCCESSFUL", "REJECTED"]:
            self.fail("[MANUAL TIMEOUT")
            self.finish()

        db.session.commit()
        return self.id

    def start(self):
        task_type = "periodic" if self.periodic else "lone"
        logger.info(f"executing {task_type} task: {self.task.name}!")
        self.state = "RUNNING"
        self.started_at = dt.now()
        self.retries = self.bind.request.retries
        self.max_retries = self.bind.max_retries
        db.session.commit()

    def reject(self, msg):
        self.state = "REJECTED"
        self.finished_at = datetime.datetime.now()
        logger.info(msg)
        db.session.commit()

    def fail(self, error):
        if self.task.periodic:
            self.task.last_failed = dt.now()

        self.state = "FAILED"
        logger.error("f{self.task.name} - (FAILED) - ERROR: '{error}'")
        db.session.commit()

    def revoke(self):
        revoke_msg = f"REVOKED [run_id: {self.id}/cel_id: {self.celery_id}]"
        logger.info(f"{self.task.name} - ({revoke_msg})")
        current_app.celery.control.revoke(self.celery_id)

    def retry(self, error):
        db.session.rollback()
        self.state = "RETRYING"

        countdown = self.get_countdown()
        retry_msg = (
            f"RETRYING - [{(self.retries + 1)}/{self.bind.max_retries}]"
            f"[COUNTDOWN: {countdown}]"
        )
        logger.error(f"{self.task.name} - ({retry_msg}) - ERROR: {error}")

        self.bind.request.kwargs.update({"task_run_id": self.id})
        self.bind.retry(countdown=countdown)
        db.session.commit()

    def complete(self):
        if self.periodic:
            self.task.last_run = self.started_at

        self.state = "SUCCESSFUL"
        db.session.commit()

    def get_countdown(self, exponent=3, maximum=None):
        minimum = minimum or TaskRun.MAX_COUNTDOWN
        current = (exponent ** (self.retries + 1))
        return maximum if current > maximum else current

    def finish(self):
        self.finished_at = dt.now()
        self.started_at = self.started_at or self.finished_at
        self.execution_time = (self.finished_at - self.started_at).total_seconds()
        finish_msg = f"FINISHED/{self.state.value} - [EXECUTION TIME: {self.execution_time}]"
        logger.info(f"{self.task.name} - ({finish_msg})")

    def skip(self):
        self.reject("[SKIPPING]")
        return False

    def is_retrying(self):
        return self.state.value == "RETRYING"


@event.listens_for(TaskRun, 'after_update')
def receive_after_update(mapper, connection, target):
    state = db.inspect(target)

    changes = {}
    for attr in state.attrs:
        hist = attr.load_history()
        if hist.has_changes():
            changes[attr.key] = hist.added

    if changes.get("state"):
        logger.info(f"[TASK STATE UPDATED - {target.get_state()}]")


    # def func_log(self, name, level="INFO", **kwargs):
    #     msg = "executing function: '{}', kwargs: {}".format(name, kwargs)
    #     self.log(msg=msg, level=level)
