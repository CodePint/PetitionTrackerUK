from .models import (
    Petition,
    Record,
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency
)
from flask import current_app
from PetitionTracker import celery
import datetime as dt
import os

from celery.utils.log import get_task_logger
task_logger = get_task_logger(__name__)

@celery.task(name='onboard_task')
def onboard_task(id):
    task_logger.info('celery worker onboarding petition ID: {}'.format(id))
    Petition.onboard(id)

@celery.task(name='poll_task')
def poll_task(id):
    task_logger.info('celery worker polling petition ID: {}'.format(id))
    petition = Petition.query.get(id)
    petition.poll()


@celery.task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5},
    name='populate_petitions_task'
)
@task_handler(task_name='populate_petitions_task')
def populate_petitions_task(state):
    task_logger.info('populating petitions - [State: {}]'.format(state))
    start = strfttime()

    petitions = Petition.populate(state=state)

    end = strfttime()
    task_logger.info("start: {}, end: {}, populated: {}".format(start, end, str(len(petitions))))
    return True

@celery.task(
    autoretry_for=(Exception,),
    retry_kwargs={'max_retries': 5},
    name='poll_petitions_task'
)
@task_handler(task_name='poll_petitions_task')
def poll_petitions_task():
    task_logger.info('polling all petitions')
    start = strfttime()
    records = Petition.poll_all()
    end = strfttime()
    task_logger.info("start: {}, end: {}, polled: {}.".format(start, end, str(len(records))))
    return True

def strfttime():
    return dt.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")