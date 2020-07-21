from .models import (
    Petition,
    Record,
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency
)
from flask import current_app
from PetitionTracker import celery
import os
import time, datetime

@celery.task()
def onboard_task(id):
    print('celery worker onboarding petition ID: {}'.format(id))
    Petition.onboard(id)

@celery.task()
def poll_task(id):
    print('celery worker polling petition ID: {}'.format(id))
    petition = Petition.query.get(id)
    petition.poll()

@celery.task()
def populate_petitions_task(state):
    print('celery worker populating petitions - [State: {}]'.format(state))
    start = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    petitions = Petition.populate(state=state)
    end = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    
    write_populate_petitions_task_result(start, end, petitions)
    return True

@celery.task()
def poll_petitions_task():
    print('celery worker polling petitions')
    start = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    records = Petition.poll_all()

    end = datetime.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    write_poll_petitions_task_result(start, end, records)
    return True

def write_poll_petitions_task_result(start, end, records):
    directory = 'development/celery'
    file = 'polled.txt'
    path = os.path.join(os.getcwd(), directory, file)
    num_records = len(records)
    with open(path, "a") as file:
        file.write("started poll at: {}".format(start))
        file.write("\n")
        file.write("finished poll at: {}".format(end))
        file.write("\n")
        file.write("Records created: {}".format(str(num_records)))

def write_populate_petitions_task_result(start, end, petitions):
    directory = 'development/celery'
    file = 'populated.txt'
    path = os.path.join(os.getcwd(), directory, file)
    num_petitions = len(petitions)
    with open(path, "a") as file:
        file.write("started populating at: {}".format(start))
        file.write("\n")
        file.write("finished populating at: {}".format(end))
        file.write("\n")
        file.write("Petitions created: {}".format(str(num_petitions)))