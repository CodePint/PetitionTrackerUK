from flask import current_app
from .models import Petition, Record
from .models import PetitionSchema, RecordSchema
from application import celery
from application.lib.celery.decorators import task_handler
import datetime as dt
import os

@celery.task(name='onboard_task')
def onboard_task(logger, *args, **kwargs):
    logger.info('celery worker onboarding petition ID: {}'.format(id))
    petition = Petition.onboard(id)
    if petition:
        return PetitionSchema().dump(petition)

@celery.task(name='poll_self_task')
def poll_self_task(logger, *args, **kwargs):
    logger.info('celery worker polling petition ID: {}'.format(id))
    petition = Petition.query.get(kwargs["id"])
    record = petition.poll_self(logger=logger, **kwargs)
    if record:
        return RecordSchema().dump(record)

@celery.task(name='poll_petitions_task')
@task_handler()
def poll_petitions_task(logger, *args, **kwargs):
    records = Petition.poll(logger=logger, **kwargs)
    logger.info("Petitions polled: {}".format(len(records)))
    if records and any(records):
        return RecordSchema(many=True).dump(records)

@celery.task(name='populate_petitions_task')
@task_handler()
def populate_petitions_task(logger, *args, **kwargs):
    petitions = Petition.populate(logger=logger, **kwargs)
    logger.info("Petitions onboarded: {}".format(len(petitions)))
    if petitions and any(petitions):
        return PetitionSchema(many=True).dump(petitions)

@celery.task(name='update_trending_petitions_pos_task')
@task_handler()
def update_trending_petitions_pos_task(logger, *args, **kwargs):
    petitions = Petition.update_trending(logger=logger, **kwargs)
    logger.info("Petitions updated: {} (default remaining to pos 0)".format(len(petitions)))
    if petitions and any(petitions):
        return PetitionSchema(many=True).dump(petitions)