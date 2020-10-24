from celery import Celery
from celery.schedules import crontab
from application import celery as app

@app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    pass
    # Calls test('hello') every 10 seconds.
    # sender.add_periodic_task(10.0, test.s('hello'), name='add every 10')

    # # Calls test('world') every 30 seconds
    # sender.add_periodic_task(30.0, test.s('world'), expires=10)
