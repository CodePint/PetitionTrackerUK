#!/bin/bash

celery -A application.lib.celery.workers.beat_scheduler.celery beat \
--loglevel=INFO