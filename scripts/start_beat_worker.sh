#!/bin/bash
celery -A PetitionTracker.lib.celery.workers.beat_worker.celery beat \
--loglevel=INFO \
-f logs/celery/schedule/beat.log
