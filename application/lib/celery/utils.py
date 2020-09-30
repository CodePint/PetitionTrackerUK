from application.models import Setting
from .schedule import scheduled_tasks
from .templates import template_tasks
from celery import Celery
from flask import current_app
import os, time, datetime

class CeleryUtils():

    @classmethod
    def init_celery(cls, celery, app):
        celery.conf.update(app.config)
        celery.conf.default_queue = 'default'
        celery.conf.timezone = 'UTC'
        
        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        return celery

    # init celery schedule
    @classmethod
    def init_beat(cls, app, celery):
        with app.app_context():
            schedule = scheduled_tasks()
            celery.conf.beat_schedule = schedule
            return schedule

    # init celery schedule
    @classmethod
    def run_task(cls, name, app=None, perodic=False, func_kwargs={}, async_kwargs={}):
        app = app or current_app
        with app.app_context():
            task = template_tasks()[name]
            task['func_kwargs'].update(func_kwargs)
            task['async_kwargs'].update(async_kwargs)
            task['func_kwargs']['periodic'] = perodic
            task['function'].s(**task['func_kwargs']).apply_async(**task['async_kwargs'])

    @classmethod
    def run_scheduled_tasks(cls, app=None):
        app = app or current_app
        with app.app_context():
            tasks = template_tasks()
            for task_name, params in template_tasks().items():
                if params.get('startup'):
                    params['function'].s(**params['func_kwargs']).apply_async(**params['async_kwargs'])
