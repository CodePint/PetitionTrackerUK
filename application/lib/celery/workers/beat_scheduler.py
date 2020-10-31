from application import celery, create_app
from application.lib.celery.utils import CeleryUtils
from celery.utils.log import get_task_logger

app = create_app(worker=__name__)
app.app_context().push()
from application.lib.celery.signals import *

CeleryUtils.init_beat(app)
