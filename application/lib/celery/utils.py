from celery import Celery
from celery import task as CeleryTask
from celery_once import QueueOnce
from datetime import timedelta
from itertools import chain
from celery.contrib import rdb
from celery.schedules import crontab
from .loader import TaskLoader
from .tasks import context_tasks
from flask import current_app as c_app
import os, time, datetime, uuid, logging
# from application import models

logger = logging.getLogger(__name__)



class CeleryUtils():

    @classmethod
    def make(cls, config, name=__name__,):
        return Celery(name, broker=config.REDIS_BROKER)

    @classmethod
    def init_base(cls, app, celery):
        celery.conf.update(app.config["CELERY_CONFIG"].BASE)
        celery.conf["task_publish_retry_policy"] = cls.retry_policy()
        celery.Task = context_tasks(app, celery, name="ContextTask")
        return celery

    @classmethod
    def init_once(cls, app, celery):
        celery.conf.ONCE = app.config["CELERY_CONFIG"].ONCE
        celery.QueueOnce = context_tasks(app, celery, name="ContextQueueOnce")
        return celery

    @classmethod
    def init_beat(cls, app):
        app.celery.conf.update(app.config["CELERY_CONFIG"].REDBEAT)
        with c_app.app_context():
            Task = c_app.models.Task
            schedule = Task.query.filter_by(periodic=True, enabled=True).all()
            return [cls.add_periodic_task(task) for task in schedule]

    @classmethod
    def add_periodic_task(cls, task):
        with c_app.app_context():
            function = TaskLoader.get_func(task.name, task.module)
            schedule = cls.parse_schedule(task.schedule)
            ## task.opts must be unpacked for queues to function ##
            return c_app.celery.add_periodic_task(
                sig=function.s(**task.kwargs),
                schedule=schedule,
                **task.opts
            )

    # initializes predefined template tasks with posgtres Task model
    @classmethod
    def init_templates(cls, overwrite=False):
        logger.info("initializing task templates")
        with c_app.app_context():
            Task = c_app.models.Task
            templates = TaskLoader().tasks["templates"]
            templates = list(chain.from_iterable(templates.values()))
            init_func = Task.create_or_update if overwrite else Task.get_or_create
            tasks = [init_func(**task) for task in templates]
            c_app.db.session.add_all(tasks)
            c_app.db.session.commit()

            return tasks

    # initializes predefined scheduled tasks with posgtres Task model
    # adds the newly created tasks to the celery beat schedule
    @classmethod
    def init_schedule(cls, overwrite=False):
        logger.info("initializing task schedule")
        with c_app.app_context():
            Task = c_app.models.Task
            schedule = TaskLoader().tasks["schedule"]
            init_func = Task.create_or_update if overwrite else Task.get_or_create
            tasks = [init_func(**task) for task in schedule]
            c_app.db.session.add_all(tasks)
            c_app.db.session.commit()

            return tasks

    @classmethod
    def send_startup_tasks(cls, module, disabled=False):
        if disabled:
            return False

        logger.info(f"sending startup tasks for: {module}")
        with c_app.app_context():
            Task = c_app.models.Task
            startup_query = Task.query.filter_by(enabled=True, startup=True, module=module)
            return cls.send_from_query(query=startup_query)

    @classmethod
    def send_from_query(cls, query, kwargs=None, opts=None):
        kwargs, opts = kwargs or {}, opts or {}
        with c_app.app_context():
            tasks = query.all()
            return [cls.send_task(task=t, kwargs=kwargs, opts=opts) for t in tasks]

    @classmethod
    def send_task(cls, name=None, key=None, task=None, unique=False, kwargs=None, opts=None):
        kwargs, opts = kwargs or {}, opts or {}
        with c_app.app_context():
            if not task:
                Task = c_app.models.Task
                task = Task.get(name, key, will_raise=True)
            if unique:
                kwargs.update({"unique": True, "uuid":  uuid.uuid1()})

            function = TaskLoader.get_func(task.name, task.module)
            logger.info(f"sending task {name}/{key}")
            function_signature = function.s(**{**task.kwargs, **kwargs})
            return function_signature.apply_async(**{**task.opts, **opts})

    @classmethod
    def retry_policy(cls):
        return {
            "max_retries": 3,
            "interval_start": 10,
            "interval_step": 15,
            "interval_max": 60,
        }

    @classmethod
    def parse_schedule(cls, schedule):
        if schedule.get("timedelta"):
            return timedelta(**schedule["timedelta"])
        if schedule.get("crontab"):
            return crontab(**schedule["crontab"])
        if schedule.get("integer"):
            return int(schedule["integer"])


