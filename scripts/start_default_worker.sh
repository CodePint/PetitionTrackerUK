#!/bin/bash
celery -A PetitionTracker.lib.celery.workers.task_worker.celery worker \
--loglevel=INFO \
--pool=solo \
--queue default \
-f logs/celery/workers/default.log