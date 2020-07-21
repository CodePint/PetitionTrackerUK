from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from celery import Celery
from dotenv import load_dotenv
import os
import click

def load_models():
    from PetitionTracker import models
    from PetitionTracker.tracker import models

def init_data():
    from PetitionTracker.tracker.data import geographies

def init_tasks():
    from PetitionTracker import tasks as shared_tasks
    from PetitionTracker.tracker import tasks as tracker_tasks
    return {'shared': shared_tasks, 'tracker': tracker_tasks}

def make_celery(app_name=__name__):
    redis_uri = os.getenv('REDIS_URI')
    return Celery(app_name, backend=redis_uri, broker=redis_uri)

def init_celery_utils():
    from PetitionTracker.lib.celery.utils import CeleryUtils as celery_utils
    return celery_utils

def init_settings(app):
    from PetitionTracker.models import Setting
    return Setting

def init_views(app):
    from PetitionTracker import tracker
    from PetitionTracker import pages

    app.register_blueprint(tracker.bp)
    app.register_blueprint(pages.bp)


ENV_FILE = '.env'
load_dotenv(dotenv_path=ENV_FILE, override=True)
from .config import Config

db = SQLAlchemy()
celery = make_celery()
load_models()
migrate = Migrate(foo="hello")
init_data()


class SubFlask(Flask):
  def run(self, host=None, port=None, debug=None, load_dotenv=True, **options):
    if not self.debug or os.getenv('WERKZEUG_RUN_MAIN') == 'true':
        self.after_create()
        super(SubFlask, self).run(host=host, port=port, debug=debug, load_dotenv=load_dotenv, **options)

    def after_create(self):
        with self.app_context():
            self.app.tasks = init_tasks()
            self.app.settings.configure(self.app.config['DEFAULT_SETTINGS'])
            self.app.celery_utils.run_on_startup()
            self.app.celery_utils.init_beat(self.app.celery)

def create_app():
    # create app and load configuration variables
    app = SubFlask(__name__, instance_relative_config=False)
    app.config.from_object(Config)

    with app.app_context():
        # configure database
        app.db = db
        db.init_app(app)
        migrate.init_app(app, db)
        app.settings = init_settings(app)

        # configure celery
        app.celery_utils = init_celery_utils()
        app.celery = app.celery_utils.init_celery(celery, app)

        # configure views
        init_views(app)

    @app.cli.command("test")
    def after_run():
        app.settings.configure(app.config['DEFAULT_SETTINGS'])
        app.celery_utils.run_on_startup()
        app.celery_utils.init_beat(app.celery)

    @app.shell_context_processor
    def get_shell_context():
        from PetitionTracker import shell

        context = shell.make_context()
        context['db'] = db
        context['app'] = app
        
        return context

    return app


