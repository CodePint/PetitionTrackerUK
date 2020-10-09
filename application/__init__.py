from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_compress import Compress

from celery import Celery
from types import SimpleNamespace
from dotenv import load_dotenv

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
    from application.models import Task, TaskRun, TaskLog
    from application.lib.celery.schedule import Schedule
    app.task_schedule = Schedule()
    app.tasks = {'shared': shared_tasks, 'tracker': tracker_tasks}

def make_celery(app_name=__name__):
    redis_uri = os.getenv('REDIS_URI')
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

def init_logging():
    config = {}
    config["level"] = Config.LOG_LEVEL
    config["datefmt"] = '%Y-%m-%d,%H:%M:%S'
    config["format"] ='%(asctime)s.%(msecs)03d %(levelname)s {%(module)s} %(message)s'
    logging.basicConfig(**config)

def init_app_logger(app):
    from application.models import Logger, AppLog
    app.app_logger = Logger(model='app', worker="FLASK", module=__name__)

from .config import Config
Config.init_env()
Config.import_env()
init_logging()

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

        # init_app_logger()
        init_app_logger(app)

        # configure celery
        init_celery(app)

        # configure views
        compress.init_app(app)
        init_views(app)

        # configure imports
        init_settings(app)
        init_models(app)
        init_schemas(app)
        init_tasks(app)

    @app.cli.command("init-settings")
    def configure_settings():
        print("configuring default values for settings table")
        current_app.settings.configure(current_app.config['DEFAULT_SETTINGS'])

    @app.cli.command("init-tasks")
    def configure_tasks():
        print("configuring default values for periodic tasks")
        current_app.models.Task.init_tasks(current_app.config['PERIODIC_TASK_SETTINGS'])

    @app.cli.command("run-tracker-tasks")
    def run_overdue_tasks():
        print("checking for overdue tracker tasks")
        current_app.celery_utils.run_tasks_for(queue="tracker")
    
    @app.cli.command("react")
    def run_yarn():
        print("starting react frontend")
        subprocess.run('cd frontend && yarn run start', shell=True)

    @app.cli.command("update-geographies")
    def update_geography_data():
        print("updating geography application choices")
        from application.tracker import geographies

    @app.cli.command("db-create")
    def create_db():
        print("creating database")
        current_app.db.create_all()

    @app.cli.command("db-drop")
    def drop_db():
        print("droping database")
        current_app.db.drop_all()

    @app.cli.command("db-drop-alembic")
    def reset_alembic():
        print("dropping alembic database table")
        current_app.db.engine.connect().execute("DROP TABLE IF EXISTS alembic_version")
    
    @app.cli.command("db-delete-petitions")
    def delete_all_petitions():
        print("deleting all petitions...")
        petitions = current_app.models.Petition.query.all()
        for p in petitions:
            current_app.db.session.delete(p)
        db.session.commit()
        print("Petitions deleted: {}".format(len(petitions)))

    @app.cli.command("celery-purge")
    def purge_celery():
        print("purging celery!")
        current_app.celery.control.purge()

    @app.shell_context_processor
    def get_shell_context():
        from application import context
        context = context.make()
        app.config["DEBUG"] = True
        app.config["SQLALCHEMY_ECHO"] = True

        context["db"] = db
        context["app"] = app
        return context

    return app


