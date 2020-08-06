from application.models import Setting
from application.tracker.models import (
    Petition,
    PetitionSchema,
    PetitionNestedSchema,
    Record,
    RecordNestedSchema,
    RecordSchema,
    SignaturesByCountry,
    SignaturesByCountrySchema,
    SignaturesByRegion,
    SignaturesByRegionSchema,
    SignaturesByConstituency,
    SignaturesByConstituencySchema
)

def make_context():
    context = {}
    context.update(context_models())
    context.update(context_schemas())
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
        'SignaturesByCountrySchema': SignaturesByCountrySchema,
        'SignaturesByRegionSchema': SignaturesByRegion,
        'SignaturesByConstituencySchema': SignaturesByConstituency
    }