from PetitionTracker import celery, create_app
from PetitionTracker.celery import CeleryUtils

app = create_app()
CeleryUtils.init(celery, app)
