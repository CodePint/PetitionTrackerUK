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

@celery.task()
def onboard_task(id):
    print('celery worker onboarding petition ID: {}'.format(id))
    Petition.onboard(id)

@celery.task()
def poll_task(id):
    print('celery worker polling petition ID: {}'.format(id))
    petition = Petition.query.get(id)
    petition.poll()

@celery.task()
def populate_petitions_task(state):
    task_logger.info('populating petitions - [State: {}]'.format(state))
    start = strfttime()

    petitions = Petition.populate(state=state)

    end = strfttime()
    task_logger.info("start: {}, end: {}, populated: {}".format(start, end, str(len(petitions))))
    return True

@celery.task()
def poll_petitions_task():
    task_logger.info('polling all petitions')
    start = strfttime()
    records = Petition.poll_all()
    end = strfttime()
    task_logger.info("start: {}, end: {}, polled: {}.".format(start, end, str(len(records))))
    return True

def strfttime():
    return dt.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")