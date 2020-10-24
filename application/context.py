from flask import current_app

def register_context(app, db, celery):

    @app.shell_context_processor
    def context_processor():
        context = make_context()
        app.config["DEBUG"] = False
        app.config["SQLALCHEMY_ECHO"] = True

        context["db"] = db
        context["app"] = app
        context["celery"] = celery

        return context

def make_context():
    context = {}
    context.update(import_models())
    context.update(import_schemas())
    context.update(import_utils())

    return context

def import_models():
    models = {}
    models.update(import_tracker_models())
    models.update(import_task_models())
    models.update(import_setting_model())

    return models

def import_tracker_models():
    from application.tracker.models import (
        Petition,
        Record,
        SignaturesBySchema,
        SignaturesByCountry,
        SignaturesByRegion,
        SignaturesByConstituency,
    )

    return {
        "Petition": Petition,
        "Record": Record,
        "SignaturesByCountry": SignaturesByCountry,
        "SignaturesByRegion": SignaturesByRegion,
        "SignaturesByConstituency": SignaturesByConstituency
    }

def import_task_models():
    from application.models import Task, TaskRun
    return {"Task": Task, "TaskRun": TaskRun}

def import_setting_model():
    from application.models import Setting
    return {"Setting": Setting}

def import_schemas():
    from application.tracker.models import (
        PetitionSchema,
        PetitionNestedSchema,
        RecordNestedSchema,
        RecordSchema,
        SignaturesBySchema,
        SignaturesByCountrySchema,
        SignaturesByRegionSchema,
        SignaturesByConstituencySchema
    )

    return {
        "PetitionSchema": PetitionSchema,
        "PetitionNestedSchema": PetitionNestedSchema,
        "RecordSchema": RecordSchema,
        "RecordNestedSchema": RecordNestedSchema,
        "SignaturesBySchema": SignaturesBySchema,
        "SignaturesByCountrySchema": SignaturesByCountrySchema,
        "SignaturesByRegionSchema": SignaturesByRegionSchema,
        "SignaturesByConstituencySchema": SignaturesByConstituencySchema
    }

def import_utils():
    from application.tracker.utils import ViewUtils as TrackerViewUtils
    from application.lib.celery.utils import CeleryUtils
    return {"TrackerViewUtils": TrackerViewUtils, "CeleryUtils": CeleryUtils}