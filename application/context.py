

def make():
    context = {}
    context.update(import_models())
    context.update(import_schemas())
    context.update(import_utils())
    context.update(import_settings())
    context.update(import_task_models())
    context.update(import_task_logger())
    return context

def import_models():
    from application.tracker.models import (
        Petition,
        Record,
        SignaturesBySchema,
        SignaturesByCountry,
        SignaturesByRegion,
        SignaturesByConstituency,
    )
    return {
        'Petition': Petition,
        'Record': Record,
        'SignaturesByCountry': SignaturesByCountry,
        'SignaturesByRegion': SignaturesByRegion,
        'SignaturesByConstituency': SignaturesByConstituency
    }

def import_settings():
    from application.models import Setting
    return {'Setting': Setting}

def import_task_models():
    from application.models import Task, TaskRun, TaskLog
    return {'Task': Task, 'TaskRun': TaskRun, 'TaskLog': TaskLog}

def import_task_logger():
    from application.models import TaskLogger
    return {'TaskLogger': TaskLogger}

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
        'PetitionSchema': PetitionSchema,
        'PetitionNestedSchema': PetitionNestedSchema,
        'RecordSchema': RecordSchema,
        'RecordNestedSchema': RecordNestedSchema,
        'SignaturesBySchema': SignaturesBySchema,
        'SignaturesByCountrySchema': SignaturesByCountrySchema,
        'SignaturesByRegionSchema': SignaturesByRegionSchema,
        'SignaturesByConstituencySchema': SignaturesByConstituencySchema
    }

def import_utils():
    from application.tracker.utils import ViewUtils as TrackerViewUtils
    return {
        'TrackerViewUtils': TrackerViewUtils
    }