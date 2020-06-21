import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from .config import Config

def create_app():
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(Config)

    from Tracker.models import db
    db.init_app(app)
    Migrate(app, db)

from Tracker.models import (
    Petition,
    Record,
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency
)

from Tracker.models import db

from . import routes

@app.shell_context_processor
def make_shell_context():
    return { 
        'db': db,
        'Petition': Petition,
        'Record': Record,
        'SignaturesByCountry': SignaturesByCountry,
        'SignaturesByRegion': SignaturesByRegion,
        'SignaturesByConstituency': SignaturesByConstituency,
    }