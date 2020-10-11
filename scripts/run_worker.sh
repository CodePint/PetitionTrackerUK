#!/bin/bash

celery -A application.lib.celery.workers.default_worker.celery worker \
--loglevel=INFO \
--pool=solo \
--queue default
