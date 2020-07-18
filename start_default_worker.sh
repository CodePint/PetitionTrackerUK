#!/bin/bash
celery -A PetitionTracker.proj_celery.worker.celery worker --loglevel=INFO --pool=solo --queue default
