import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from .config import Config


app = Flask(__name__, instance_relative_config=True)
app.config.from_object(Config)
db = SQLAlchemy(app)

if __name__ == "__main__":
    app.run()

from . import routes
from .models import (
    Petition,
    Record,
    TotalSignatures,
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency
)

migrate = Migrate(app, db)

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