from .templates import template_tasks
from .schedule import TaskSchedule
from celery import Celery
from flask import current_app
import os, time, datetime

class CeleryUtils():

    # initializes celery base config
    @classmethod
    def init_celery(cls, celery, app):
        celery.conf.update(app.config)
        celery.conf["DEFAULT_QUEUE"] = "default"
        celery.conf["TIMEZONE"] = "Europe/London"
        celery.conf["CELERY_ENABLE_UTC"] = False

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    kwargs['queue'] =  self.request.delivery_info['routing_key']
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        return celery

    # initializes celery beat schedule
    @classmethod
    def init_beat(cls, app, celery):
        with app.app_context():
            schedule = TaskSchedule()
            app.task_schedule = schedule
            celery.conf.beat_schedule = schedule.tasks
            return schedule

    # run a task template with optional periodic and async celery arguments
    # func_kwargs overrides the actual predefined task arguments
    # can be executed from corresponding Task object via Task.Run
    @classmethod
    def run_task(cls, name, app=None, periodic=False, func_kwargs={}, async_kwargs={}):
        app = app or current_app
        with app.app_context():
            task = template_tasks()[name]
            task['func_kwargs'].update(func_kwargs)
            task['async_kwargs'].update(async_kwargs)
            task['func_kwargs']['periodic'] = periodic
            task['function'].s(**task['func_kwargs']).apply_async(**task['async_kwargs'])

    # runs tasks by queue type, optional startup param (will check if task is a startup task)
    # tasks must still be enabled or the handler will reject them
    @classmethod
    def run_tasks_for(cls, app=None, queue="default", periodic=True, startup=False):
        app = app or current_app

        def will_run(task, queue, startup):
            found = task and task_queue == queue
            run_on_startup = not startup and task.run_on_startup
            return found and run_on_startup

        with app.app_context():
            tasks = template_tasks()
            for task_name, params in template_tasks().items():
                task = current_app.models.Task.get(task_name)
                task_queue = params['async_kwargs']['queue']
                params['func_kwargs']['periodic'] = periodic
                # if task not found or task disabled or queue does not match: next
                if not task or not task.enabled or (task_queue != queue):
                    next
                # if not startup param or if startup param and task.run_on_startup 
                if not startup or task.run_on_startup:
                    print("running: {}".format(task.name))
                    params['function'].s(**params['func_kwargs']).apply_async(**params['async_kwargs'])