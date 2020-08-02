from flask import current_app
from .models import Petition, Record
from application import celery
from application.lib.celery.decorators import task_handler
import datetime as dt
import os

from celery.utils.log import get_task_logger
task_logger = get_task_logger(__name__)

@celery.task(name='onboard_task')
def onboard_task(id):
    task_logger.info('celery worker onboarding petition ID: {}'.format(id))
    Petition.onboard(id)
    return True

@celery.task(name='poll_task')
def poll_task(id):
    task_logger.info('celery worker polling petition ID: {}'.format(id))
    petition = Petition.query.get(id)
    petition.poll()
    return True

@celery.task(name='populate_petitions_task')
@task_handler()
def populate_petitions_task(task_name='populate_petitions_task', *args, **kwargs):
    records = Petition.poll_all()
    task_logger.info("Petitions polled: {}".format(str(len(records))))
    return True

@celery.task(name='poll_petitions_task')
@task_handler()
def poll_petitions_task(task_name='poll_petitions_task', *args, **kwargs):
    records = Petition.poll_all()
    task_logger.info("Petitions polled: {}".format(str(len(records))))
    return True
