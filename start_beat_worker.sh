#!/bin/bash
celery -A PetitionTracker.lib.celery.worker.celery beat --loglevel=INFO


