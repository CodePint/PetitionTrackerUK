#!/bin/bash

exec pipenv run celery -A application.lib.celery.workers.application_worker.celery worker \
--loglevel=INFO \
--pool=solo \
--queue application
