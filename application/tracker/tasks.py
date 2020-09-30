from flask import current_app
from .models import Petition, Record
from application import celery
from application.lib.celery.decorators import task_handler
import datetime as dt
import os

from celery.utils.log import get_task_logger
task_logger = get_task_logger(__name__)

@celery.task(name='onboard_task')
def onboard_task(logger, *args, **kwargs):
    logger.info('celery worker onboarding petition ID: {}'.format(id))
    petition = Petition.onboard(id)
    return petition

@celery.task(name='poll_self_task')
def poll_self_task(logger, *args, **kwargs):
    logger.info('celery worker polling petition ID: {}'.format(id))
    petition = Petition.query.get(kwargs["id"])
    record = petition.poll_self(**kwargs)
    return record

@celery.task(name='poll_petitions_task')
@task_handler()
def poll_petitions_task(logger, *args, **kwargs):
    records = Petition.poll(**kwargs)
    logger.info("Petitions polled: {}".format(len(records)))
    return records

@celery.task(name='populate_petitions_task')
@task_handler()
def populate_petitions_task(logger, *args, **kwargs):
    petitions = Petition.populate(**kwargs)
    logger.info("Petitions onboarded: {}".format(len(petitions)))
    return petitions

@celery.task(name='update_trending_petitions_pos_task')
@task_handler()
def update_trending_petitions_pos_task(logger, *args, **kwargs):
    responses = Petition.update_trending(**kwargs)
    logger.info("Petitions updated: {} (default remaining to pos 0)".format(len(responses or [])))
    return responses