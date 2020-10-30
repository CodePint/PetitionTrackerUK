from application.logger.formatter import EFKJsonFormatter
from flask import Flask, request
from flask import current_app as c_app
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
        handler = getattr(task, "handler", None)

        if task and request:
            log_record["task_name"] = task.name
            log_record["celery_id"] = request.id

        if handler:
            log_record["task_key"] = handler.get("task", {}).get("key")
            log_record["run_id"] = handler["id"]
            log_record["state"] = handler["state"]
