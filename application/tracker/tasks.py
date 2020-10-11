from flask import current_app
from .models import Petition, Record
from .models import PetitionSchema, RecordSchema
from application.lib.celery.decorators import task_handler
from application import celery
import datetime as dt
import os

@celery.task(bind=True, name='onboard_task')
def onboard_task(self, *args, **kwargs):
    petition = Petition.onboard(id)
    if petition: return PetitionSchema().dump(petition)

@celery.task(bind=True, name='poll_self_task')
def poll_self_task(self, *args, **kwargs):
    petition = Petition.query.get(kwargs["id"])
    record = petition.poll_self(logger=self.logger, **kwargs)
    if record: return RecordSchema().dump(record)

@celery.task(bind=True, name='poll_petitions_task')
@task_handler()
def poll_petitions_task(self, *args, **kwargs):
    records = Petition.poll(logger=self.logger, **kwargs)
    self.logger.info("Petitions polled: {}".format(len(records)))
    if records: return [r.petition_id for r in records]

@celery.task(bind=True, name='populate_petitions_task', max_retries=3)
@task_handler()
def populate_petitions_task(self, *args, **kwargs):
    petitions = Petition.populate(logger=self.logger, **kwargs)
    self.logger.info("Petitions onboarded: {}".format(len(petitions)))
    if petitions: return [p.id for p in petitions]

@celery.task(bind=True, name='update_trending_petitions_pos_task')
@task_handler()
def update_trending_petitions_pos_task(self, *args, **kwargs):
    petitions = Petition.update_trending(logger=self.logger, **kwargs)
    self.logger.info("Petitions updated: {}".format(len(petitions)))
    if petitions: return [p.id for p in petitions]
