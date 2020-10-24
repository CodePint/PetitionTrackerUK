from application import celery, create_app, init_beat
from application.lib.celery.utils import CeleryUtils
from celery.utils.log import get_task_logger

app = create_app()
with app.app_context():
    app.celery_utils.init_beat()