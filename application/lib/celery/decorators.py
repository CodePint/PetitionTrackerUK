from flask import current_app
from functools import wraps
from datetime import datetime as dt

def task_handler(*args, **kwargs):
    def wrapper(func):
        @wraps(func)
        def handle(self, *args, **kwargs):
            from .utils import CeleryUtils
            from application.models import Task
            
            self.request.kwargs.update(**kwargs)
            task = Task.get(kwargs['task_name'])
            if not task:
                raise RuntimeError("Task not found: {}".format(kwargs['task_name']))
                
            task_run = task.init_run(self)
            if task_run.periodic:
                if task_run.is_retrying() or task_run.is_overdue():
                    return task_run.execute(func, *args, **kwargs)
                else:
                    return task_run.skip()
            else:
                return task_run.execute(func, *args, **kwargs)
            return False
        return handle
    return wrapper


def if_enabled(task_name):
    def wrapper(func):
        @wraps(func)
        def get(*args, **kwargs):
            from application.models import Task
            task = Task.get(task_name)                
            return func(*args, task=task, **kwargs) if task and task.enabled else {}
        return get
    return wrapper