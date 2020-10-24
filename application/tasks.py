from flask import current_app
from application import celery
from application.lib.celery.decorators import task_handler
from datetime import datetime as dt
import logging, time, os

logger = logging.getLogger(__name__)


@celery.task(bind=True, name='test_task')
# @task_handler()
def test_task(self, *args, **kwargs):
    print("running_test_task!!!!")
    greeting = kwargs.get("greeting")
    logger.info(f"running test task, greeting:  {greeting}")
    file_path = os.path.join(os.getcwd(), "debug/celery", "test_task.txt")

    with open(file_path, "a") as file:
        file.write(f"Test Task: {greeting} - {dt.now()}")

    logger.info("ending test task!")
    return greeting
