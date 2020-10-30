#!/bin/bash

celery -A application.lib.celery.workers.beat_scheduler.celery beat \
-S redbeat.RedBeatScheduler \
--loglevel=DEBUG