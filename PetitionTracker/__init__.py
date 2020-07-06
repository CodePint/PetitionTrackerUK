import os
from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from celery import Celery

from .config import Config
from .celery import CeleryUtils

db = SQLAlchemy()


def load_models():
    from PetitionTracker.tracker import models

def init_extensions(app):
    from PetitionTracker.tracker.data import geographies

def make_celery(app_name=__name__):
    redis_uri = os.getenv('REDIS_URI')
    return Celery(app_name, backend=redis_uri, broker=redis_uri)

def init_views(app):
    from PetitionTracker import tracker
    from PetitionTracker import pages

    app.register_blueprint(tracker.bp)
    app.register_blueprint(pages.bp)

load_models()
celery = make_celery()

def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    init_extensions(app)

    with app.app_context():
        app.db = db
        db.init_app(app)
        init_views(app)
        Migrate(app, db)
        init_views(app)

    @app.shell_context_processor
    def get_shell_context():
        from PetitionTracker import shell

        context = shell.make_context()
        context['db'] = db
        context['app'] = app
        
        return context

    return app
