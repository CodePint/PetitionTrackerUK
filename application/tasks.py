from flask import current_app
from application import celery
from application.lib.celery.decorators import task_handler
from datetime import datetime
import time
import os

@celery.task(bind=True, name='test_task', max_retires=3)
@task_handler()
def test_task(self, *args, **kwargs):
    directory = 'debug/celery'
    timestamp = datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    self.logger.info("running test task! - {}".format(timestamp))
    file_path = os.path.join(os.getcwd(), directory, kwargs['file'])
    with open(file_path, "a") as file:
        file.write(timestamp)
        file.write("\n")
        file.write(kwargs['content'])
        file.write("\n")
        
    self.logger.info("ending test task!")
    return kwargs['content']
