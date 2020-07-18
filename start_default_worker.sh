#!/bin/bash
celery -A PetitionTracker.lib.celery.worker.celery worker --loglevel=INFO --pool=solo --queue default
