from flask import current_app
from functools import wraps
from datetime import datetime as dt
from time import sleep
import logging

logger = logging.getLogger(__name__)


def task_handler(*args, **kwargs):
    from application.models import Task
    def wrapper(func):
        @wraps(func)
        def handle(self, **kwargs):
            import pdb
            pdb.set_trace()
            # sleep_time = kwargs.pop("sleep_time", 30)
            # logger.info(f"sleeping task: {name}-{key}, for: {sleep_time}s")
            # sleep(sleep_time)
            # kwargs["queue"] = "application"
            self.request.kwargs.update(**kwargs)
            # logger.info(f"handling task: {name}")

            # task = Task.get(name, key, will_raise=True)
            # task_run = task.init_run(bind=self)
            # return task_run.execute(func, *args, **kwargs)

            # if task_run.is_retrying() or task_run.will_run():
            #     return task_run.execute(func, *args, **kwargs)
            # else:
            #     return task_run.skip()

        return handle
    return wrapper
