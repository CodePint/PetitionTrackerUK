from application.logger.formatter import EFKJsonFormatter
from application.lib.celery.logger import TaskLogFormatter

import logging

def setup_handlers(logger, template={},**kwargs):
    template["context"] = ["%(levelname)s", "%(name)s", "%(message)s"]
    template["timestamp"] = ["%(asctime)s, %(msecs)s"]
    if kwargs.get("worker"):
        task_handler(logger, template)
    else:
        app_handler(logger, template)

def app_handler(logger, template):
    handler = logging.StreamHandler()
    formatter = EFKJsonFormatter(fmt=make_fmt(template), datefmt="%Y-%m-%dT%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def task_handler(logger, template, **kwargs):
    handler = logging.StreamHandler()
    template["task"] =  ["%(task_name)s", "%(celery_id)s"]
    template["run"] =  ["%(run_id)s", "%(task_key)s", "%(state)s"]
    formatter = TaskLogFormatter(fmt=make_fmt(template), datefmt="%Y-%m-%dT%H:%M:%S")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

def make_fmt(template):
    return " ".join([v for k in template.values() for v in k])