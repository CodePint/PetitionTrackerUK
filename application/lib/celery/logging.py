import logging

class TaskLogFormatter(logging.Formatter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from celery._state import get_current_task
            self.get_current_task = get_current_task
        except ImportError:
            self.get_current_task = lambda: None

    def format(self, record):
        task = self.get_current_task()
        if task and task.request:
            record.__dict__.update(task_id=task.request.id, task_name=task.name)
        else:
            record.__dict__.setdefault('task_name', '')
            record.__dict__.setdefault('task_id', '')
        return super().format(record)

