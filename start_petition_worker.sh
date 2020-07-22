#!/bin/bash
celery -A PetitionTracker.lib.celery.workers.task_worker.celery worker \
--loglevel=INFO \
--pool=solo \
--queue periodic_remote_petition \
-f logs/celery/workers/petitions.log


