import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

from .config import Config
app = Flask(__name__, instance_relative_config=True)
app.config.from_object(Config)

from PetitionTracker.models import (
    Petition,
    Record,
    TotalSignatures,
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency
)

from PetitionTracker.models import db
db.init_app(app)

Migrate(app, db)

from . import routes


@app.shell_context_processor
def make_shell_context():
    return { 
        'db': db,
        'Petition': Petition,
        'Record': Record,
        'TotalSignatures': TotalSignatures,
        'SignaturesByCountry': SignaturesByCountry,
        'SignaturesByRegion': SignaturesByRegion,
        'SignaturesByConstituency': SignaturesByConstituency,
    }