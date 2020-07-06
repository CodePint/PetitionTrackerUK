from celery import Celery

class CeleryUtils():
    
    @classmethod
    def init_celery(cls, celery, app):
        celery.conf.update(app.config)

        class ContextTask(celery.Task):
            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return self.run(*args, **kwargs)

        celery.Task = ContextTask
        return celery


