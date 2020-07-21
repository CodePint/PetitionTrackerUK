from PetitionTracker import celery, create_app, init_beat
from PetitionTracker.lib.celery.utils import CeleryUtils

app = create_app()
init_beat(app)
