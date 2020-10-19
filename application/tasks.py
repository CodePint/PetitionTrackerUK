from flask import current_app
from application import celery
from application.lib.celery.decorators import task_handler
from datetime import datetime
import logging
import time
import os


logger = logging.getLogger(__name__)


@celery.task(bind=True, name='test_task', max_retires=3)
@task_handler()
def test_task(self, *args, **kwargs):
    logger.info("logging from task!")
    from application.tracker.models import Petition
    result = Petition.task_log(greeting="hello world!")
    logger.info(result)
    logger.debug("exiting from task")

    return True

