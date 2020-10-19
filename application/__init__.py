from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_compress import Compress
from psycopg2cffi import compat

from celery import Celery
from types import SimpleNamespace
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger

from application import context
from application.config import Config
from application.context import register_context
from application.cli import register_cli
from application.logging.formatter import EFKJsonFormatter

import logging, subprocess, os, click

def init_namespaced_context(app, name, data):
    namespace = SimpleNamespace(name=name)
    for k, v in data.items(): setattr(namespace, k, v)
    setattr(app, name, namespace)

def init_models(app):
    init_namespaced_context(app, "models", context.import_models())

def init_schemas(app):
    init_namespaced_context(app, "schemas", context.import_schemas())

def init_context(app):
    from application import context
    app.context = context

def init_tasks(app):
    from application import tasks as shared_tasks
    from application.tracker import tasks as tracker_tasks
    from application.models import Task, TaskRun, TaskLog
    from application.lib.celery.schedule import TaskSchedule
    app.TaskSchedule = TaskSchedule
    app.tasks = { "shared": shared_tasks, "tracker": tracker_tasks}

def make_celery(app_name=__name__):
    redis_uri = os.getenv("REDIS_URI")
    return Celery(app_name, backend=redis_uri, broker=redis_uri)

def init_celery(app):
    from application.lib.celery.utils import CeleryUtils
    app.celery_utils = CeleryUtils
    app.celery = CeleryUtils.init_celery(celery, app)

def init_settings(app):
    from application.models import Setting
    app.settings = Setting

def init_views(app):
    from application import tracker
    from application import pages

    app.register_blueprint(tracker.bp)
    app.register_blueprint(pages.bp)

def init_beat(app=None):
    if not app:
        app = current_app
    app.celery_utils.init_beat(app, app.celery)

def load_models():
    from application import models
    from application.tracker import models

def init_logging(app, **kwargs):
    if kwargs.get("worker"):
        init_task_logging(app, **kwargs)
    else:
        init_app_logging(app, **kwargs)

def init_app_logging(app, **kwargs):
    logger = logging.getLogger(__name__)
    logger.setLevel(Config.LOG_LEVEL)
    json_handler = logging.StreamHandler()
    formatter_template = "%(asctime)s %(levelname)s %(name)s %(message)s"
    formatter = EFKJsonFormatter(formatter_template)
    json_handler.setFormatter(formatter)
    logger.addHandler(json_handler)

def init_task_logging(app, **kwargs):
    from application.lib.celery.logging import TaskLogFormatter
    logger = logging.getLogger()
    sh = logging.StreamHandler()
    formatter_template = "%(asctime)s - %(task_id)s - %(task_name)s - %(name)s - %(levelname)s - %(message)s"
    formatter = TaskLogFormatter(formatter_template)
    sh.setFormatter(formatter)
    logger.setLevel(logging.INFO)
    logger.addHandler(sh)

# init config
Config.init()

# init database/adapter
compat.register()
db = SQLAlchemy()

# init models/migrations
load_models()
migrate = Migrate()

# init celery object
celery = make_celery()

# init compress object
compress = Compress()


def create_app(**kwargs):
    # create app and load configuration variables
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    cors = CORS(app, resources={r"*": {"origins": "*"}}) 

    with app.app_context():
        init_logging(app, **kwargs)

        # configure database
        app.db = db
        db.init_app(app)
        migrate.init_app(app, db)

        # configure celery
        init_celery(app)
        init_tasks(app)

        # configure views
        compress.init_app(app)
        init_views(app)

        # configure imports
        init_models(app)
        init_settings(app)
        init_schemas(app)
        init_context(app)
    
    register_cli(app, db, celery)
    register_context(app, db, celery)

    return app


