#!/bin/bash
celery -A application.lib.celery.workers.task_worker.celery worker \
--loglevel=INFO \
--pool=solo \
--queue tracker \
-f logs/celery/workers/tracker.log


