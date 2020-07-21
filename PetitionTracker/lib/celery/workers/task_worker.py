from PetitionTracker import celery, create_app
from PetitionTracker.lib.celery.utils import CeleryUtils

app = create_app()
app.celery_utils.run_overdue_tasks(app=app)
