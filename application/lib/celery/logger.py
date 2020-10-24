from application.logger.formatter import EFKJsonFormatter
from flask import Flask, request, current_app
import logging


class TaskLogFormatter(EFKJsonFormatter):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            from celery._state import get_current_task
            self.get_current_task = get_current_task
        except ImportError:
            self.get_current_task = lambda: None

    def add_fields(self, log_record, record, message_dict):
        log_record = super().add_fields(log_record, record, message_dict)

        task = self.get_current_task()
        request = getattr(task, "request", None)
        task_run = getattr(task, "task_run", None)

        if task and request:
            log_record["task_name"] = task.name
            log_record["celery_id"] = request.id

        if task_run:
            log_record["task_key"] = task_run.task.key
            log_record["run_id"] = task_run.id
            log_record["state"] = task_run.state
