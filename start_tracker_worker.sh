#!/bin/bash
celery -A PetitionTracker.lib.celery.workers.task_worker.celery worker \
--loglevel=INFO \
--pool=solo \
--queue tracker \
-f logs/celery/workers/petitions.log


