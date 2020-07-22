from flask import current_app
from PetitionTracker import celery
from PetitionTracker.lib.celery.decorators import task_handler
from datetime import datetime
import time
import os

from celery.utils.log import get_task_logger
task_logger = get_task_logger(__name__)


@celery.task(name='test_task')
@task_handler()
def test_task(task_name='test_task', *args, **kwargs):
    timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    task_logger.info("running test task!!!!!! - {}".format(timestamp))
    current_app.logger.info("test task!")
    print("executing beat task: {}".format(kwargs['content']))
    directory = 'development/celery'
    file_path = os.path.join(os.getcwd(), directory, kwargs['file'])
    with open(file_path, "a") as file:
        file.write(timestamp)
        file.write("\n")
        file.write(kwargs['content'])
        file.write("\n")
        
    task_logger.info("ending test task!!!!!!")
    return True
