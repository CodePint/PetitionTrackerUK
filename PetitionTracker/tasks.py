from flask import current_app
from PetitionTracker import celery
from PetitionTracker.lib.celery.decorators import task_handler
from datetime import datetime
import time
import os

@celery.task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5},
    name='test_task'
)
@task_handler(task_name='test_task')
def test_task(task_name, file, content):
    print("executing beat task: {}".format(content))
    directory = 'development/celery'
    file_path = os.path.join(os.getcwd(), directory, file)
    with open(file_path, "a") as file:
        now = datetime.now() 
        timestamp = now.strftime("%m/%d/%Y, %H:%M:%S")
        file.write(timestamp)
        file.write("\n")
        file.write(content)
        file.write("\n")