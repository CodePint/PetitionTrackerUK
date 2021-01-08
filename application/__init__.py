from flask import Flask
from flask import current_app as c_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_compress import Compress
from psycopg2cffi import compat
from types import SimpleNamespace
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger
from celery import Celery
import redis

from application.config import Config
from application import context as Context
from application import cli as Cli
from application.lib.celery.utils import CeleryUtils

import logging, subprocess, os, click

def init_namespaced_context(app, name, data):
    namespace = SimpleNamespace(name=name)
    for k, v in data.items(): setattr(namespace, k, v)
    setattr(app, name, namespace)

def init_models(app):
    from application.models import Setting, Task, TaskRun
    init_namespaced_context(app, "models", Context.import_models())

def init_schemas(app):
    init_namespaced_context(app, "schemas", Context.import_schemas())

def init_views(app):
    from application import tracker, pages
    app.register_blueprint(tracker.bp)
    app.register_blueprint(pages.bp)

def init_celery(app, celery):
    from application.lib.celery.utils import CeleryUtils
    app.celery_utils = CeleryUtils
    app.celery = CeleryUtils.init_base(app=app, celery=celery)
    app.celery = CeleryUtils.init_once(app=app, celery=celery)
    return celery

def make_celery():
    from application.lib.celery.utils import CeleryUtils
    return CeleryUtils.make(Config, __name__)

def make_redis():
    return redis.Redis(host=Config.REDIS_HOST, port=Config.REDIS_PORT, db=0)

def load_tasks():
    from application import tasks
    from application.tracker import tasks

def load_models():
    from application import models
    from application.tracker import models

def init_logging(**kwargs):
    from application.lib.logging import initialize
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.getLevelName(Config.LOG_LEVEL))
    initialize(root_logger, **kwargs)

def init_config(config=None, **settings):
    if not config:
        from application.config import Config
    return Config.load()

Config.load()

# init database/adapter
compat.register()
db = SQLAlchemy()

# init models/migrations
load_models()
migrate = Migrate()

# init celery object
redis_db = make_redis()
celery = make_celery()

# init compress object
compress = Compress()

def create_app(name=__name__, **kwargs):

    # create app and load configuration variables
    app = Flask(name, instance_relative_config=False)
    app.config.from_object(Config)
    app.context = Context
    init_logging(**kwargs)

    # configure cross origin resources
    origins = {"origins": app.config["CORS_ORIGINS"]}
    cors = CORS(app, resources={r"*": origins})

    with app.app_context():
        # configure database
        app.db = db
        db.init_app(app)
        migrate.init_app(app, db)

        # configure imports
        init_models(app)
        init_schemas(app)

        # configure celery
        app.redis = redis_db
        init_celery(app, celery)
        load_tasks()

        # configure views
        compress.init_app(app)
        init_views(app)

    Context.register(app, db, celery)
    Cli.register(app, db, celery)

    return app