from flask import current_app
from functools import wraps
from datetime import datetime as dt

def task_handler( *args, **kwargs):
    def wrapper(func):
        @wraps(func)
        def handle(*args, **kwargs):
            from .utils import CeleryUtils
            from application.models import Task

            periodic = kwargs.get('periodic')
            queue = kwargs.pop("queue", "default")
            worker = "{}_WORKER".format(queue.upper())
            task_name = kwargs.get("task_name", "name empty")
            task = Task.get(task_name)
            
            if task:
                task_run = task.init_run(periodic=periodic, args=kwargs)
                task_run.init_logger(worker)
                kwargs.update({"logger": task_run.logger})

                if task.enabled and task_run.periodic:
                    if task_run.is_overdue():
                        return task_run.execute(func, **kwargs)
                    else:
                        return task_run.skip()
                else:
                    return task_run.execute(func,**kwargs)
            else:
                current_app.app_logger.error("Task not found: {}".format(task_name))
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