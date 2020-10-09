from application import celery, create_app, init_beat
from application.lib.celery.utils import CeleryUtils

app = create_app()
init_beat(app)
app.celery_utils.run_tasks_for(app=app, queue="tracker", startup=True)