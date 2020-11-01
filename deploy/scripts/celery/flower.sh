#!/bin/bash

exec pipenv run celery flower -A application.lib.celery.workers.flower_monitor.celery \
--url_prefix=flower \
--persistent=True \
--broker=redis://redis