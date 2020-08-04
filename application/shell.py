from application.models import Setting
from application.tracker.models import (
    Petition,
    PetitionSchema,
    Record,
    RecordSchema,
    RecordAbrvSchema,
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
        'RecordSchema': RecordSchema,
        'RecordAbrvSchema': RecordAbrvSchema,
        'SignaturesByCountrySchema': SignaturesByCountrySchema,
        'SignaturesByRegionSchema': SignaturesByRegion,
        'SignaturesByConstituencySchema': SignaturesByConstituency
    }