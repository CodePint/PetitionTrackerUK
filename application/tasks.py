from flask import current_app
from application import celery
from application.lib.celery.decorators import task_handler
from datetime import datetime
import time
import os

@celery.task(name='test_task')
@task_handler()
def test_task(logger, *args, **kwargs):
    directory = 'development/celery'
    timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    logger.info("running test task! - {}".format(timestamp))
    file_path = os.path.join(os.getcwd(), directory, kwargs['file'])
    with open(file_path, "a") as file:
        file.write(timestamp)
        file.write("\n")
        file.write(kwargs['content'])
        file.write("\n")
        
    logger.info("ending test task!")
    return True
