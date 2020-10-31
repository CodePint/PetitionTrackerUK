from .models import Petition, Record
from .models import PetitionSchema, RecordSchema
from flask import current_app as c_app
from application import celery
from celery_once import QueueOnce

import datetime as dt
import os, logging

logger = logging.getLogger(__name__)

celery_opts = {"bind": True}
once_opts = {
    "base": celery.QueueOnce,
    "once": {"graceful": True}
}

@celery.task(name='onboard_task', **celery_opts, **once_opts)
def onboard_self_task(self, runner=None, *args, **kwargs):
    with runner.execute(bind=self):
        petition = Petition.onboard(id)
        return runner.commit(result=petition, schema=PetitionSchema())

@celery.task(name='poll_self_task', **celery_opts, **once_opts)
def poll_self_task(self, runner=None, *args, **kwargs):
    with runner.execute(bind=self):
        petition = Petition.query.get(kwargs["id"])
        record = petition.poll_self(**kwargs)
        return runner.commit(result=record, schema=RecordSchema())

@celery.task(name='base_poll_task', **celery_opts, **once_opts)
def base_poll_task(self, runner=None, *args, **kwargs):
    with runner.execute(bind=self):
        records = Petition.poll(**kwargs)
        logger.info("Petitions polled: {}".format(len(records)))
        return runner.commit([r.petition_id for r in records])

@celery.task(name='geo_poll_task', **celery_opts, **once_opts)
def geo_poll_task(self, runner=None, *args, **kwargs):
    with runner.execute(bind=self):
        records = Petition.poll(geo=True **kwargs)
        logger.info("Petitions polled: {}".format(len(records)))
        return runner.commit([r.petition_id for r in records])

@celery.task(name='populate_petitions_task', **celery_opts, **once_opts)
def populate_petitions_task(self, runner=None, *args, **kwargs):
    with runner.execute(bind=self):
        petitions = Petition.populate(**kwargs)
        logger.info("Petitions onboarded: {}".format(len(petitions)))
        return runner.commit([p.id for p in petitions])

@celery.task(name='update_trending_pos_task', **celery_opts, **once_opts)
def update_trending_pos_task(self, runner=None, *args, **kwargs):
    with runner.execute(bind=self):
        petitions = Petition.update_trending(logger=self.logger, **kwargs)
        logger.info("Petitions updated: {}".format(len(petitions)))
        return runner.commit([p.id for p in petitions])
