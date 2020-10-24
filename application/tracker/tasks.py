from flask import current_app
from .models import Petition, Record
from .models import PetitionSchema, RecordSchema
from application.lib.celery.decorators import task_handler
from application import celery
import datetime as dt
import os, logging

logger = logging.getLogger(__name__)

@celery.task(bind=True, name='onboard_task')
def onboard_self_task(self, *args, **kwargs):
    petition = Petition.onboard(id)
    if petition: return PetitionSchema().dump(petition)

@celery.task(bind=True, name='poll_self_task')
def poll_self_task(self, *args, **kwargs):
    petition = Petition.query.get(kwargs["id"])
    record = petition.poll_self(**kwargs)
    if record: return RecordSchema().dump(record)

@celery.task(bind=True, name='base_poll_task')
@task_handler()
def base_poll_task(self, *args, **kwargs):
    records = Petition.poll(**kwargs)
    logger.info("Petitions polled: {}".format(len(records)))
    if records: return [r.petition_id for r in records]

@celery.task(bind=True, name='geo_poll_task')
@task_handler()
def geo_poll_task(self, *args, **kwargs):
    records = Petition.poll(geo=True **kwargs)
    logger.info("Petitions polled: {}".format(len(records)))
    if records: return [r.petition_id for r in records]

@celery.task(bind=True, name='populate_petitions_task', max_retries=3)
@task_handler()
def populate_petitions_task(self, *args, **kwargs):
    petitions = Petition.populate(**kwargs)
    logger.info("Petitions onboarded: {}".format(len(petitions)))
    if petitions: return [p.id for p in petitions]

@celery.task(bind=True, name='update_trending_pos_task')
@task_handler()
def update_trending_pos_task(self, *args, **kwargs):
    petitions = Petition.update_trending(logger=self.logger, **kwargs)
    logger.info("Petitions updated: {}".format(len(petitions)))
    if petitions: return [p.id for p in petitions]
