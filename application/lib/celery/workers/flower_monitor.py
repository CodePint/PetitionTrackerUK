from application import celery, create_app
from application.lib.celery.utils import CeleryUtils

app = create_app()