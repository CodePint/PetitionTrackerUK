from application.models import Setting
from application.tracker.models import (
    Petition,
    PetitionSchema,
    PetitionNestedSchema,
    Record,
    RecordNestedSchema,
    RecordSchema,
    SignaturesBySchema,
    SignaturesByCountry,
    SignaturesByCountrySchema,
    SignaturesByRegion,
    SignaturesByRegionSchema,
    SignaturesByConstituency,
    SignaturesByConstituencySchema
)
from application.tracker.utils import ViewUtils as TrackerViewUtils

def make_context():
    context = {}
    context.update(context_models())
    context.update(context_schemas())
    context.update(context_utils())
    return context

def context_models():
    return {
        'Setting': Setting,
        'Petition': Petition,
        'Record': Record,
        'SignaturesByCountry': SignaturesByCountry,
        'SignaturesByRegion': SignaturesByRegion,
        'SignaturesByConstituency': SignaturesByConstituency
    }

def context_schemas():
    return {
        'PetitionSchema': PetitionSchema,
        'PetitionNestedSchema': PetitionNestedSchema,
        'RecordSchema': RecordSchema,
        'RecordNestedSchema': RecordNestedSchema,
        'SignaturesBySchema': SignaturesBySchema,
        'SignaturesByCountrySchema': SignaturesByCountrySchema,
        'SignaturesByRegionSchema': SignaturesByRegion,
        'SignaturesByConstituencySchema': SignaturesByConstituency
    }

def context_utils():
    return {
        'TrackerViewUtils': TrackerViewUtils
    }