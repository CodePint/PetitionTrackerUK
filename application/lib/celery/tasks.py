from celery import Celery
from celery import task as CeleryTask
from celery_once import QueueOnce
from celery.result import EagerResult
from celery import states
from celery_once.tasks import AlreadyQueued
from flask import current_app as c_app
import logging

logger = logging.getLogger(__name__)

def context_tasks(app, celery, name):
    from application.models import AlreadyPending
    from application.models import Task as DBTask
    from application.models import TaskRun

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    class ContextQueueOnce(QueueOnce):
        def apply_async(self, args=None, kwargs=None, **options):
            with app.app_context():
                # parse options from function, task and config
                once_opts = options.get('once', {})
                graceful_pending = once_opts.get('graceful_pending', True)
                graceful_lock = once_opts.get('graceful', self.once.get('graceful', False))
                timeout = once_opts.get('timeout', self.once.get('timeout', self.default_timeout))

                # always get the redis lock key
                lock_key = self.get_key(args, kwargs)
                if not options.get('retries'):
                    # get database task if not retrying
                    db_task = DBTask.get(self.name, kwargs["key"], will_raise=True)
                    try:
                        # raise if pending or locked else init lock and handler
                        self.raise_if_pending(db_task)
                        self.once_backend.raise_or_lock(lock_key, timeout=timeout)
                        kwargs["id"] = self.init_handler(db_task, lock_key).id
                    # handle the exception if graceful option == True, else reraise
                    except AlreadyPending as e:
                        if  graceful_pending:
                            return self.reject_eager(lock_key, e)
                        raise e
                    except AlreadyQueued as e:
                        if graceful_lock:
                            return self.reject_eager(lock_key, e)
                        raise e

                async_result = super(QueueOnce, self).apply_async(args, kwargs, **options)
                async_result.lock_key = lock_key

                return async_result

        def raise_if_pending(self, db_task):
            pending = db_task.where("PENDING")
            if any(pending):
                raise AlreadyPending(db_task, [p.id for p in pending])

        def reject_eager(self, lock_key, error):
            # log exception, then return eager result with error and lock key
            logger.info(f"{error.__class__.__name__}, {error.message}")
            eager_result = EagerResult(None, None, states.REJECTED)
            eager_result.error = error
            EagerResult.lock_key = lock_key

            return eager_result

        def init_handler(self, db_task, lock_key):
            logger.info(f"initializing task handler for: {db_task.name}/{db_task.key}")
            handler = TaskRun(task_id=db_task.id, lock_key=lock_key, state="PENDING")
            app.db.session.add(handler)
            app.db.session.commit()
            handler.set("PENDING")
            app.db.session.commit()

            return handler


        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super(ContextQueueOnce, self).__call__(*args, **kwargs)

    tasks = {
        "ContextQueueOnce": ContextQueueOnce,
        "ContextTask": ContextTask
    }

    return tasks[name]