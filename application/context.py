from flask import current_app

def make():
    context = {}
    context.update(import_models())
    context.update(import_schemas())
    context.update(import_utils())
    context.update(import_logger())
    context.update(import_decorators())

    return context

def import_models():
    models = {}
    models.update(import_tracker_models())
    models.update(import_log_models())
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

def import_log_models():
    from application.models import BaseLog, AppLog, TaskLog
    return {"AppLog": AppLog, "TaskLog": TaskLog}

def import_setting_model():
    from application.models import Setting
    return {"Setting": Setting}

def import_logger():
    from application.models import Logger
    return {"Logger": Logger}

def import_decorators():
    from application.decorators import with_logging, will_save_log
    return {"with_logging": with_logging, "will_save_log": will_save_log}

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

def drop_tables():
    print("dropping all tables!")

    with current_app.app_context():
        dropped = []
        for name, model in import_models().items():
            try:
                    model.__table__.drop(current_app.db.engine)
                    dropped.append(name)
            except Exception as error:
                    print("Table: '{}', does not exist".format(name))

        print("Tables dropped: {}".format(dropped))
        return dropped

def drop_alembic():
    print("dropping alembic database table!")
    current_app.db.engine.connect().execute("DROP TABLE IF EXISTS alembic_version")

def delete_all_petitions():
    print("deleting all petitions!")
    with current_app.app_context(): 
        petitions = current_app.models.Petition.query.all()
        for p in petitions:
            current_app.db.session.delete(p)
        current_app.db.session.commit()

        print("Petitions deleted: {}".format(len(petitions)))
        return petitions

def check_tables():
    with current_app.app_context():
        app_models = import_models().items()
        tables = [
            name for name, model in app_models
            if current_app.db.engine.has_table(model.__tablename__)
        ]

        print("Tables ({}/{}) found: {}".format(len(tables), len(app_models), tables))
        return tables