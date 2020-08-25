from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_compress import Compress

from celery import Celery
from dotenv import load_dotenv
from types import SimpleNamespace

import logging
import subprocess
import click
import os

from application import context

def init_namespaced_context(app, name, data):
    namespace = SimpleNamespace(name=name)
    for k, v in data.items(): setattr(namespace, k, v)
    setattr(app, name, namespace)

def init_models(app):
    init_namespaced_context(app, 'models', context.import_models())

def init_schemas(app):
    init_namespaced_context(app, 'schemas', context.import_schemas())

def init_tasks(app):
    from application import tasks as shared_tasks
    from application.tracker import tasks as tracker_tasks
    app.tasks = {'shared': shared_tasks, 'tracker': tracker_tasks}

def make_celery(app_name=__name__):
    redis_uri = os.getenv('REDIS_URI')
    return Celery(app_name, backend=redis_uri, broker=redis_uri)

def init_celery_utils():
    from application.lib.celery.utils import CeleryUtils as celery_utils
    return celery_utils

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

ENV_FILE = '.env'
load_dotenv(dotenv_path=ENV_FILE, override=True)
from .config import Config
logging.basicConfig(filename=Config.LOG_FILE, level=Config.LOG_LEVEL)

db = SQLAlchemy()
celery = make_celery()
load_models()
migrate = Migrate()
compress = Compress()

def create_app():
    # create app and load configuration variables
    app = Flask(__name__, instance_relative_config=False)
    cors = CORS(app, resources={r"*": {"origins": Config.CORS_RESOURCE_ORIGINS}})
    app.config.from_object(Config)

    with app.app_context():
        # configure database
        app.db = db
        db.init_app(app)
        migrate.init_app(app, db)

        # configure celery
        app.celery_utils = init_celery_utils()
        app.celery = app.celery_utils.init_celery(celery, app)

        # configure views
        compress.init_app(app)
        init_views(app)

        # configure imports
        init_settings(app)
        init_models(app)
        init_schemas(app)
        init_tasks(app)

    @app.cli.command("configure")
    def configure():
        print("configuring default values for settings table")
        current_app.settings.configure(current_app.config['DEFAULT_SETTINGS'])

    @app.cli.command("run-overdue-tasks")
    def run_overdue_tasks():
        print("checking for overdue celery tasks")
        current_app.celery_utils.run_overdue_tasks()

    @app.cli.command("update-geographies")
    def update_geography_data():
        print("updating geography application choices")
        from application.tracker import geographies

    @app.cli.command("react")
    def run_yarn():
        print("starting react frontend")
        subprocess.run('cd frontend && yarn start', shell=True)

    
    @app.shell_context_processor
    def get_shell_context():
        from application import context

        context = context.make()
        context['db'] = db
        context['app'] = app
        
        return context

    return app


