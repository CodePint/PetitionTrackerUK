from .utils import CeleryUtils
from flask import current_app
from functools import wraps
from datetime import datetime as dt

from celery.utils.log import get_task_logger
celery_logger = get_task_logger(__name__)


def task_handler( *args, **kwargs):
    def task_runner(func, task, task_run, logger, periodic=False, **kwargs):
        try:
            kwargs.update({"logger": logger})
            logger.info("Starting task!")
            task_run.state = "RUNNING"
            current_app.db.session.commit()
            
            result = func(**kwargs)

            if periodic:
                task.last_run = task_run.started_at

            logger.info("Task completed succesfully")
            task_run.state = "COMPLETED"
        except Exception as error:
            if periodic:
                task.last_failed = dt.now()
            
            task_run.state = "FAILED"
            logger.fatal("Task failed, Error: {}".format(error))
            raise error
        finally:
            task_run.finished_at = dt.now()
            execution_time = (task_run.finished_at - task_run.started_at).total_seconds()
            task_run.execution_time = execution_time
            current_app.db.session.commit()
        
        return result

    def outer_wrapper(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            task = current_app.task.get(kwargs.get("task_name", "N/A"))
            if task:
                task_run = task.init_run(started_at=dt.now(), task_args=kwargs)
                logger = current_app.task_logger(task_run)
                if kwargs.get('periodic') and task.enabled:
                    if task.is_overdue():
                        return task_runner(func, task, task_run, logger, periodic=True **kwargs)
                    else:
                        task_run.reject()
                        logger.debug("Skipping task (run recently)")
                else:
                    return task_runner(func, task, task_run, logger, **kwargs)
            return False
        return inner_wrapper
    return outer_wrapper


