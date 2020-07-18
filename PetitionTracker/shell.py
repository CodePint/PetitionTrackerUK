from PetitionTracker.tracker.models import (
    Petition,
    Record,
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency,
)

from PetitionTracker.models import Setting

def make_context():
    context = {}
    context.update(context_models())
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