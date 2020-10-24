from .loader import TaskLoader
from celery import Celery, signature
from celery_once import QueueOnce
from flask import current_app as curr_app
from datetime import timedelta
from time import sleep
from itertools import chain
import os, time, datetime, logging

logger = logging.getLogger(__name__)

class CeleryUtils():

    # @classmethod
    # def make(cls, config, name=__name__,):
    #     celery = Celery(name, backend=config.REDIS_URI, broker=config.REDIS_URI)
    #     # celery.conf.update(vars(config))
    # celery.conf["TASK_DEFAULT_QUEUE"] = "default"
    # celery.conf["TIMEZONE"] = "Europe/London"
    #     celery.conf["CELERY_ENABLE_UTC"] = False

    #     # once_config = {"settings": {}}
    #     # once_config["backend"] = "celery_once.backends.Redis"
    #     # once_config["settings"]["url"] = config.REDIS_URI
    #     # once_config["settings"]["default_timout"] = config.CELERY_ONCE_TIMEOUT
    #     # celery.conf.ONCE = once_config

    #     return celery

    # # initializes celery base config
    # @classmethod
    # def init(cls, app, celery):
    #     class ContextTask(celery.Task):
    #         def __call__(self, *args, **kwargs):
    #             with app.app_context():
    #                 self.request.kwargs = self.request.kwargs or {}
    #                 return self.run(*args, **kwargs)

    #     celery.Task = ContextTask
    #     # celery.QueueOnce = cls.init_once(celery, app)
    #     app.celery_utils = CeleryUtils

    #     return celery

    # initializes celery base config

    @classmethod
    def init_celery(cls, celery, app):
        celery.conf.update(app.config)
        celery.conf.update(app.config)
        celery.conf["DEFAULT_QUEUE"] = "default"
        celery.conf["TIMEZONE"] = "Europe/London"
        celery.conf["CELERY_ENABLE_UTC"] = False

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    # kwargs['queue'] =  self.request.delivery_info['routing_key']
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        return celery

    # @classmethod
    # def init_once(cls, celery, app):
    #     class ContextQueueOnce(QueueOnce):
    #         def __call__(self, *args, **kwargs):
    #             with app.app_context():
    #                 return super(ContextQueueOnce, self).__call__(*args, **kwargs)

    #     return ContextQueueOnce

    @classmethod
    def init_beat(cls):
        with curr_app.app_context():
            Task = curr_app.models.Task
            schedule = Task.query.filter_by(periodic=True, enabled=True).all()
            return [cls.add_periodic_task(task) for task in schedule]

    @classmethod
    def add_periodic_task(cls, task):
        with curr_app.app_context():
            function = TaskLoader.get_func(task.name, task.module)
            return curr_app.celery.add_periodic_task(
                sig=signature(function(**task.kwargs)),
                schedule=timedelta(**task.interval),
                opts=task.options
            )

    # initializes predefined template tasks with posgtres Task model
    @classmethod
    def init_db_templates(cls, overwrite=False):
        with curr_app.app_context():
            Task = curr_app.models.Task
            templates = TaskLoader().tasks["templates"]
            templates = list(chain.from_iterable(templates.values()))
            init_func = Task.create_or_update if overwrite else Task.get_or_create
            tasks = [init_func(**task) for task in templates]
            curr_app.db.session.add_all(tasks)
            curr_app.db.session.commit()

            return tasks

    # initializes predefined scheduled tasks with posgtres Task model
    # adds the newly created tasks to the celery beat schedule
    @classmethod
    def init_db_schedule(cls, overwrite=False):
        with curr_app.app_context():
            Task = curr_app.models.Task
            schedule = TaskLoader().tasks["schedule"]
            init_func = Task.create_or_update if overwrite else Task.get_or_create
            tasks = [init_func(**task) for task in schedule]
            curr_app.db.session.add_all(tasks)
            curr_app.db.session.commit()

            return tasks

    @classmethod
    def send_startup_tasks(cls):
        with curr_app.app_context():
            Task = curr_app.models.Task
            run_on_startup = Task.query.filter_by(enabled=True, startup=True)
            return cls.run_tasks_from(query=run_on_startup)

    @classmethod
    def send_tasks_from(cls, query, force=False, kwargs={}, opts={}):
        with curr_app.app_context():
            tasks = query.all()
            return [cls.run_task(task=t, force=force, kwargs=kwargs, opts=opts) for t in tasks]

    @classmethod
    def send_task(cls, name=None, key=None, task=None, force=False, kwargs={}, opts={}):
        with curr_app.app_context():
            if not task:
                Task = curr_app.models.Task
                task = Task.get(name, key, will_raise=True)
                if not force and not task.enabled:
                    raise ValueError(f"Task {name}/{key}, is disabled")

            function = TaskLoader.get_func(task.name, task.module)
            import pdb
            pdb.set_trace()
            # return signature(function(**{**task.kwargs, **kwargs})).apply_async(**{**task.options, **opts})
            task.kwargs.pop("key")
            return signature(function(**{**task.kwargs, **kwargs})).apply_async(queue="application")

    @classmethod
    def contains_any_keys(cls, *keys, **kwargs):
        for k in keys:
            if k in kwargs.values():
                return True

    @classmethod
    def publish_retry_policy(cls):
        return {
            "max_retries": 3,
            "interval_start": 10,
            "interval_step": 15,
            "interval_max": 60,
        }


# app.celery_utils.send_task(name="test_task", key="[test_task]-[base]", kwargs={"sleep": 10}, opts={"countdown": 10})
# app.celery_utils.send_task(name="populate_petitions_task", key="[populate_task]-[base]")
# app.celery_utils.init_beat()