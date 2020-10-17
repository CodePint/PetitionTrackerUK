#!/bin/bash

celery -A application.lib.celery.workers.tracker_worker.celery worker \
--loglevel=INFO \
--pool=solo \
--queue tracker