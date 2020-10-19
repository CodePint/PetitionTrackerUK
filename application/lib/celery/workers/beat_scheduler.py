from application import celery, create_app, init_beat
from application.lib.celery.utils import CeleryUtils
from celery.utils.log import get_task_logger
logger = get_task_logger(__name__)

app = create_app()

init_beat(app)
