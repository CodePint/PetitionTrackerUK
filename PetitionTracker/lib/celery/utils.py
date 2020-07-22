from PetitionTracker.models import Setting
from .schedule import schedule_tasks, startup_tasks
from celery import Celery
from flask import current_app
import os, time

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

    @classmethod
    def init_beat(cls, app, celery):
        with app.app_context():
            schedule = schedule_tasks()
            celery.conf.beat_schedule = schedule
            return schedule

    @classmethod
    def run_overdue_tasks(cls, app=None):
        if not app:
            app = current_app
        
        with app.app_context():
            for task_name, params in startup_tasks().items():
                params['function'].s(**params['func_kwargs']).apply_async(**params['async_kwargs'])

    @classmethod
    def is_overdue(cls, task_name):
        last_run = current_app.settings.get(task_name + '__last_run')
        if not last_run:
            return True
        
        now = int(time.time())
        last_run = int(last_run)
        interval = cls.get_interval(task_name)
        if (now - last_run) >= interval:
            return True
        
        return False

    @classmethod
    def update_last_run(cls, task_name, run_at):
        key = task_name + '__last_run'
        last_run = current_app.settings.create_or_update(key=key, value=str(run_at))
        current_app.db.session.add(last_run)
        current_app.db.session.commit()

        return last_run

    @classmethod
    def get_interval(cls, task_name):
        return int(current_app.settings.get(task_name + '__interval'))
