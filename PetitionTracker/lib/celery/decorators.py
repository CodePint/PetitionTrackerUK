from .utils import CeleryUtils
from flask import current_app
from functools import wraps
# from sqlalchemy import select, func
import time


def task_handler(task_name):
    def outer_wrapper(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            run_at = int(time.time())
            if CeleryUtils.is_overdue(task_name):
                task_args = [task_name] + list(args)
                result = func(*task_args)
                CeleryUtils.update_last_run(task_name, run_at)
                return result
            else:
                print("Task {}, has been run recently - skipping".format(task_name))
                return None
        return inner_wrapper
    return outer_wrapper
