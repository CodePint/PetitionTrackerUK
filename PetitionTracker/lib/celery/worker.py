from PetitionTracker import celery, create_app
from .utils import CeleryUtils

app = create_app()
CeleryUtils.init_celery(celery, app)