import os
from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from PetitionTracker.config import Config

db = SQLAlchemy()


def load_models():
    from PetitionTracker.tracker import models

load_models()

def init_extensions(app):
    db.init_app(app)

def init_views(app):
    from PetitionTracker import tracker
    app.register_blueprint(tracker.bp)

def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)
    init_extensions(app)

    with app.app_context():
        app.db = db        
        db.init_app(app)
        init_views(app)
        migrate = Migrate(app, db)
        init_views(app)

    @app.shell_context_processor
    def get_shell_context():
        from PetitionTracker import shell

        context = shell.make_context()
        context['db'] = db
        context['app'] = app
        
        return context

    return app



