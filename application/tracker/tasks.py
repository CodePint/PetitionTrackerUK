from flask import current_app as c_app
from application import celery
from .models import Petition, Record
from .models import PetitionSchema, RecordSchema
from application.models import TaskRun as Run
import datetime as dt
import os, logging

logger = logging.getLogger(__name__)

celery_opts = {"bind": True}
once_opts = {
    "base": celery.QueueOnce,
    "once": {"graceful": True}
}

@celery.task(name='onboard_task', **celery_opts, **once_opts)
def onboard_self_task(self, *args, **kwargs):
    with Run.execute(bind=self) as handler:
        petition = Petition.onboard(id)
        return handler.commit(result=petition, schema=PetitionSchema())

@celery.task(name='poll_self_task', **celery_opts, **once_opts)
def poll_self_task(self, *args, **kwargs):
    with Run.execute(bind=self) as handler:
        petition = Petition.query.get(kwargs["id"])
        record = petition.poll_self(**kwargs)
        return handler.commit(result=record, schema=RecordSchema())

@celery.task(name='base_poll_task', **celery_opts, **once_opts)
def base_poll_task(self, *args, **kwargs):
    with Run.execute(bind=self) as handler:
        records = Petition.poll(**kwargs)
        logger.info("Petitions polled: {}".format(len(records)))
        return handler.commit(result=[r.petition_id for r in records])

@celery.task(name='geo_poll_task', **celery_opts, **once_opts)
def geo_poll_task(self, *args, **kwargs):
    with Run.execute(bind=self) as handler:
        records = Petition.poll(geo=True **kwargs)
        logger.info("Petitions polled: {}".format(len(records)))
        return handler.commit(result=[r.petition_id for r in records])

@celery.task(name='populate_task', **celery_opts, **once_opts)
def populate_task(self, *args, **kwargs):
    with Run.execute(bind=self) as handler:
        petitions = Petition.populate(**kwargs)
        logger.info("Petitions onboarded: {}".format(len(petitions)))
        return handler.commit(result=[p.id for p in petitions])

@celery.task(name='update_trending_pos_task', **celery_opts, **once_opts)
def trending_pos_task(self, *args, **kwargs):
    with Run.execute(bind=self) as handler:
        petitions = Petition.update_trending(logger=self.logger, **kwargs)
        logger.info("Petitions updated: {}".format(len(petitions)))
        return handler.commit(result=[p.id for p in petitions])
