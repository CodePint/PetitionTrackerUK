from application import celery
from application.models import TaskRun as Run
from datetime import datetime as dt
import logging, time, os
from time import sleep

logger = logging.getLogger(__name__)

celery_opts = {"bind": True}
once_opts = {
    "base": celery.QueueOnce,
    "once": {"graceful": True}
}

@celery.task(name='test_task', **celery_opts, **once_opts)
def test_task(self, *args, **kwargs):
    logger.info(f"running {self.name}!, kwargs: {kwargs}")

    with Run.execute(bind=self) as handler:
        logger.info("inside handler context!")
        return handler.commit(kwargs)