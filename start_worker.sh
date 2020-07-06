#!/bin/bash
celery worker -A PetitionTracker.worker.celery --loglevel=info --pool=solo
