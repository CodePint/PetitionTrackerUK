#!/bin/bash

celery -A application.lib.celery.workers.tracker_worker.celery worker \
--loglevel=DEBUG \
--pool=solo \
--queue tracker