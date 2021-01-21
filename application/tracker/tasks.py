from application.tracker.models import Petition, Record
from application.tracker.models import PetitionSchema, RecordSchema
from application.models import TaskRun as TaskHandler
from application import celery
import logging

logger = logging.getLogger(__name__)

celery_opts = {"bind": True}
once_opts = {
    "base": celery.QueueOnce,
    "once": {"graceful": True}
}

@celery.task(name='poll_self_task', **celery_opts, **once_opts)
def onboard_self_task(self, *args, **kwargs):
    with TaskHandler.execute(bind=self) as handler:
        kwargs = handler.getcallkwargs(Petition.onboard, kwargs)
        petition = Petition.onboard(kwargs["id"])
        logger.info(f"onboarded petition id: {petition.id}")
        return handler.commit(result=petition, schema=PetitionSchema())

@celery.task(name='poll_self_task', **celery_opts, **once_opts)
def poll_self_task(self, *args, **kwargs):
    with TaskHandler.execute(bind=self) as handler:
        petition = Petition.query.get(kwargs["id"])
        kwargs = handler.getcallkwargs(petition.poll_self, kwargs)
        record = petition.poll_self(**kwargs)
        logger.info(f"polled petition id: {petition.id}")
        return handler.commit(result=record, schema=RecordSchema())

@celery.task(name='base_poll_task', **celery_opts, **once_opts)
def base_poll_task(self, *args, **kwargs):
    with TaskHandler.execute(bind=self) as handler:
        kwargs = handler.getcallkwargs(Petition.poll, kwargs)
        records = Petition.poll(geographic=False, **kwargs)
        logger.info(f"Petitions geo polled: {records}")
        return handler.commit(result=[r.petition_id for r in records])

@celery.task(name='geo_poll_task', **celery_opts, **once_opts)
def geo_poll_task(self, *args, **kwargs):
    with TaskHandler.execute(bind=self) as handler:
        kwargs = handler.getcallkwargs(Petition.poll, kwargs)
        records = Petition.poll(geographic=True, **kwargs)
        logger.info(f"Petitions base polled: {records}")
        return handler.commit(result=[r.petition_id for r in records])

@celery.task(name='populate_task', **celery_opts, **once_opts)
def populate_task(self, *args, **kwargs):
    with TaskHandler.execute(bind=self) as handler:
        kwargs = handler.getcallkwargs(Petition.populate, kwargs)
        petitions = Petition.populate(**kwargs)
        logger.info(f"Petitions onboarded: {petitions}")
        return handler.commit(result=[p.id for p in petitions])

@celery.task(name='update_trending_pos_task', **celery_opts, **once_opts)
def update_trend_indexes_task(self, *args, **kwargs):
    with TaskHandler.execute(bind=self) as handler:
        kwargs = handler.getcallkwargs(Petition.update_trend_indexes, kwargs)
        petitions = Petition.update_trend_indexes(**kwargs)
        logger.info(f"Petitions trend indexes updated: {petitions}")
        return handler.commit(result=[p.id for p in petitions])
