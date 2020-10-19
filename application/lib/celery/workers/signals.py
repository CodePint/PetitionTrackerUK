from celery import Celery, signals

# disable log propogation
@signals.setup_logging.connect
def setup_celery_logging(**kwargs):
    pass