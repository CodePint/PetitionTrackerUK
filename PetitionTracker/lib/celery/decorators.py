from .utils import CeleryUtils
from flask import current_app
from functools import wraps
import time

from celery.utils.log import get_task_logger
task_logger = get_task_logger(__name__)

def task_handler( *args, **kwargs):
    def outer_wrapper(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            run_at = int(time.time())
            task_name = kwargs['task_name']
            if not kwargs.get('periodic'):
                return func(**kwargs)
            elif CeleryUtils.is_overdue(task_name):
                task_logger.info('running task: {}, args: {}'.format(task_name, str(args)))
                result = func(**kwargs)
                CeleryUtils.update_last_run(task_name, run_at)
                return result
            else:
                print("Task {}, has been run recently - skipping".format(task_name))
            return None
        return inner_wrapper
    return outer_wrapper
