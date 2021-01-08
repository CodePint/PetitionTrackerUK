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
                task = DBTask.get(self.name, kwargs["key"], enabled=True, will_raise=True)
                lock_key = self.get_key(args, kwargs)
                self.init_opts(task, options)
                if not self.is_retrying:
                    try:
                        # raise if pending or locked else lock and init handler
                        self.raise_if_pending(task)
                        self.once_backend.raise_or_lock(lock_key, timeout=self.timeout)
                        kwargs["id"] = self.init_handler(task, lock_key).id
                    # handle the exception if graceful else reraise
                    except AlreadyPending as e:
                        if self.graceful_pending:
                            return self.reject_eager(lock_key, e)
                        raise e
                    except AlreadyQueued as e:
                        if self.graceful_lock:
                            return self.reject_eager(lock_key, e)
                        raise e

                    # TBC: consider implementing tidy up for expired/hung task runs
                    async_result = super(QueueOnce, self).apply_async(args, kwargs, **options)
                    async_result.lock_key = lock_key
                    return async_result

        def init_opts(self, task, options):
            async_opts = options.get('once', {})
            self.is_retrying = bool(options.get("retries"))
            self.graceful_pending = async_opts.get('graceful_pending', True)
            self.graceful_lock = async_opts.get('graceful', self.once.get('graceful', False))
            self.timeout = async_opts.get('timeout', task.once_opts.get('timeout', self.default_timeout))

        def init_handler(self, task, lock_key):
            logger.info(f"initializing task handler for: {task.name}/{task.key}")
            handler = TaskRun(task_id=task.id, lock_key=lock_key, state="PENDING")
            app.db.session.add(handler)
            app.db.session.commit()
            handler.set("PENDING")
            app.db.session.commit()
            return handler

        def reject_eager(self, lock_key, error):
            logger.info(f"{error.__class__.__name__}, {error.message}")
            eager_result = EagerResult(None, None, states.REJECTED)
            eager_result.error = error
            EagerResult.lock_key = lock_key
            return eager_result

        def raise_if_pending(self, task):
            pending = task.where("PENDING").all()
            if pending:
                raise AlreadyPending(task, [p.id for p in pending])

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super(ContextQueueOnce, self).__call__(*args, **kwargs)

    tasks = {
        "ContextQueueOnce": ContextQueueOnce,
        "ContextTask": ContextTask
    }

    return tasks[name]