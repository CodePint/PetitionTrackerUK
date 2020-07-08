from PetitionTracker import celery
from .models import (
    Petition,
    Record,
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency
)

import os

@celery.task()
def tracker_test_task(content):
    directory = 'development/celery'
    file = 'tacker_test.txt'
    path = os.path.join(os.getcwd(), directory, file)
    with open(path, "w") as file:
        file.write(content)

@celery.task()
def poll(id):
    petition = Petition.query.get(id)
    petition.poll()

@celery.task()
def onboard(id):
    Petition.onboard(id)