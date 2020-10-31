from application import celery, create_app, os

app = create_app(worker=__name__)
app.app_context().push()
from application.lib.celery.signals import *

app.celery_utils.send_startup_tasks("tracker", disable=True)