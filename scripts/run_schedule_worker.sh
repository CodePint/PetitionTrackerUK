#!/bin/bash

celery -A application.lib.celery.workers.beat_worker.celery beat \
--loglevel=INFO \
-f logs/celery/schedule/beat.log
