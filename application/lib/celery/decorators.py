from flask import current_app
from functools import wraps
from datetime import datetime as dt

def task_handler(*args, **kwargs):
    def wrapper(func):
        @wraps(func)
        def handle(self, task_name, *args, **kwargs):
            from application.models import Task
            self.request.kwargs.update(**kwargs)

            task = Task.get(task_name)
            if task:
                self.task_run = task.init_run(bind=self)
            else:
                raise RuntimeError("Task not found: {}".format(task_name))

            if self.task_run.periodic:
                if self.task_run.is_retrying() or self.task_run.is_overdue():
                    return self.task_run.execute(func, *args, **kwargs)
                else:
                    return self.task_run.skip()
            else:
                return self.task_run.execute(func, *args, **kwargs)
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