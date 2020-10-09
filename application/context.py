

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
    return {"BaseLog": BaseLog, "AppLog": AppLog, "TaskLog": TaskLog}

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