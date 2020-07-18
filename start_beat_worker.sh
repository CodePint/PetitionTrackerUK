#!/bin/bash
celery -A PetitionTracker.proj_celery.worker.celery beat --loglevel=INFO
