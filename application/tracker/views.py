from . import bp
from .utils  import ViewUtils
from .models import (
    Petition,
    PetitionSchema,
    PetitionNestedSchema,
    Record,
    RecordSchema,
    RecordNestedSchema,
    SignaturesBySchema,
    SignaturesByCountry,
    SignaturesByCountrySchema,
    SignaturesByRegion,
    SignaturesByRegionSchema,
    SignaturesByConstituency,
    SignaturesByConstituencySchema,
)

from flask import (
    render_template,
    redirect,
    url_for,
    jsonify,
    current_app,
    request,
    abort
)

from sqlalchemy import or_, and_
import requests, json, os
import datetime as dt

# returns a list of petitions
@bp.route('/petitions', methods=['GET'])
def get_petitions():
    index = request.args.get('index', 1, type=int)
    items_per_page = request.args.get('items', type=int)
    state = request.args.get('state', 'all')
    params = {'items': items_per_page, 'state': state}

    context = {'state': state, 'petitions':[]}
    context['meta'] = {'query': params}

    if state == 'all':
        query = Petition.query
    else:
        # breakpoint()
        # query = Petition.query.filter_by(state=Petition.STATE_LOOKUP[state])
        query = Petition.query.filter_by(state="GG")


    if items_per_page:
        page = query.paginate(index,  items_per_page , False)
        page.curr_num = index
        petitions = page.items

        context['meta']['items'] = ViewUtils.items_for(page)
        context['meta']['pages'] = page.pages
        context['meta']['links'] = ViewUtils.get_pagination_urls(
            page,
            'tracker_bp.get_petitions',
            **params
        )
    else:
        petitions = query.all()

    if not petitions:
        return context
        
    petitions_schema = PetitionSchema(many=True)
    context['petitions'] = petitions_schema.dump(petitions)
    
    return context


@bp.route('/petition/<petition_id>', methods=['GET'])
def get_petition(petition_id):
    context = {}
    petition = Petition.get_or_404(petition_id)
    context['petition'] = PetitionSchema().dump(petition)

    if petition and request.args.get('signatures'):
        record = petition.latest_record()
        record_nested_schema = RecordNestedSchema(exclude=["id", "petition"])
        context['signatures'] = record_nested_schema.dump(record)

    return context

# returns timestamped list of total signatures for a petition
@bp.route('/petition/<petition_id>/signatures', methods=['GET'])
def get_petition_signatures(petition_id):
    index = request.args.get('index', 1, type=int)
    items_per_page = request.args.get('items', type=int)
    params = {'petition_id': petition_id}
    params['since'] = request.args.get('since', type=json.loads)
    params['between'] = request.args.get('between', type=json.loads)
    params['items_per_page'] = items_per_page

    context = {'signatures': []}
    context['meta'] = {'query': params}
    petition = Petition.get_or_404(petition_id)
    context['petition']  = PetitionSchema().dump(petition)
    query = ViewUtils.record_timestamp_query(petition, params.get('since'), params.get('between'))
    
    page = query.paginate(index, params['items_per_page'], False)
    page.curr_num = index

    if items_per_page:
        page = query.paginate(index,  items_per_page , False)
        page.curr_num = index
        records = page.items

        context['meta']['items'] = ViewUtils.items_for(page)
        context['meta']['pages'] = page.pages
        context['meta']['links'] = ViewUtils.get_pagination_urls(
            page,
            'tracker_bp.get_petition_signatures',
            **params
        )
    else:
        records = query.all()
        context['meta']['items'] = {'total': len(records)}

    if not records:
        return context

    records_schema = RecordSchema(many=True, exclude=["id"])
    context['signatures'] = records_schema.dump(records)

    return context

# returns a timestamped geographical list of signatures for a petition
@bp.route('/petition/<petition_id>/signatures_by/<geography>/', methods=['GET'])
def get_petition_signatures_by_geography(petition_id, geography):
    index = request.args.get('index', 1, type=int)
    items_per_page = request.args.get('items', type=int)
    params = {'petition_id': petition_id, 'geography': geography}
    params['since'] = request.args.get('since', type=json.loads)
    params['between'] = request.args.get('between', type=json.loads)
    params['items_per_page'] = items_per_page

    context = {'signatures': []}
    context['meta'] = {'query': params}
    petition = Petition.get_or_404(petition_id)
    context['petition']  = PetitionSchema().dump(petition)
    query = ViewUtils.record_timestamp_query(petition, params['since'],  params['between'])
    
    if items_per_page:
        page = query.paginate(index,  items_per_page , False)
        page.curr_num = index
        records = page.items

        context['meta']['items'] = ViewUtils.items_for(page)
        context['meta']['pages'] = page.pages
        context['meta']['links'] = ViewUtils.get_pagination_urls(
            page,
            'tracker_bp.get_petition_signatures_by_geography',
            **params
        )
    else:
        records = query.all()
        context['meta']['items'] = {'total': len(records)}
    
    if not records:
        return context

    record_schema = RecordSchema(exclude=["id"])
    name = 'SignaturesBy' + geography.capitalize()
    sig_exclude = ["id", "record", "timestamp", geography]
    sig_schema = SignaturesBySchema.get_schema_for(geography)(many=True, exclude=sig_exclude)
    
    for rec in records:
        record_dump = record_schema.dump(rec)
        signatures = getattr(rec, 'by_' + geography)
        record_dump[name] = sig_schema.dump(signatures)
        context['signatures'].append(record_dump)

    return context

# returns timestamped list of signatures for a petition, for a given geographical locale
@bp.route('/petition/<petition_id>/signatures_by/<geography>/<locale>', methods=['GET'])
def get_petition_signatures_by_locale(petition_id, geography, locale):
    index = request.args.get('index', 1, type=int)
    items_per_page = request.args.get('items', type=int)
    params = {'petition_id': petition_id, 'geography': geography, 'locale': locale}
    params['since'] = request.args.get('since', type=json.loads)
    params['between'] = request.args.get('between', type=json.loads)
    params['items_per_page'] = items_per_page

    context = {'signatures': []}
    context['meta'] = {'query': params}
    petition = Petition.get_or_404(petition_id)
    context['petition']  = PetitionSchema().dump(petition)

    sig_attrs = Record.signature_model_attributes([geography])
    locale = Record.get_sig_choice(geography, locale)['code']
    query = ViewUtils.record_timestamp_query(petition, params['since'], params['between'] )
    query = query.filter(sig_attrs[geography]['relationship'].any(sig_attrs[geography]['model'].code == locale))
    
    if items_per_page:
        page = query.paginate(index,  items_per_page, False)
        page.curr_num = index
        records = page.items

        context['meta']['items'] = ViewUtils.items_for(page)
        context['meta']['pages'] = page.pages
        context['meta']['links'] = ViewUtils.get_pagination_urls(
            page,
            'tracker_bp.get_petition_signatures_by_locale',
            **params
        )
    else:
        records = query.all()
        context['meta']['items'] = {'total': len(records)}

    if not records:
        return context

    record_schema = RecordSchema(exclude=["id"])
    sig_exclude = ["id", "record", geography, "timestamp"]
    sig_schema = sig_attrs[geography]['schema_class'](exclude=sig_exclude)
    for rec in records:
        record_dump = record_schema.dump(rec)
        sig_by = rec.signatures_by(geography, locale)
        record_dump[sig_attrs[geography]['name']] = sig_schema.dump(sig_by)
        context['signatures'].append(record_dump)

    return context

@bp.route('/petition/<petition_id>/signatures_by', methods=['POST'])
def get_petition_signatures_comparison(petition_id):
    index = request.args.get('index', 1, type=int)
    items_per_page = request.args.get('items', type=int)
    params = request.json
    params['items_per_page'] = items_per_page
    params['petition_id'] = petition_id

    context = {'signatures': []}
    context['meta'] = {'query': params}
    petition = Petition.get_or_404(petition_id)
    context['petition']  = PetitionSchema().dump(petition)
    query = ViewUtils.record_timestamp_query(petition, params.get('since'), params.get('between'))

    geographies = params['signatures_by'].keys()
    sig_exclude = ["id", "record", "timestamp"]
    sig_attrs = Record.signature_model_attributes(geographies)

    selects = []
    for geo in geographies:
        sig_attrs[geo]['schema'] = sig_attrs[geo]['schema_class'](exclude=sig_exclude + [geo])
        sig_attrs[geo]['locales'] = [
            Record.get_sig_choice(geo, l)['code']
            for l in params['signatures_by'][geo]
        ]
        selects.append(
            sig_attrs[geo]['relationship'].any(
            sig_attrs[geo]['model'].code.in_(
            sig_attrs[geo]['locales']
        )))

    query = query.filter(or_(*selects))

    if items_per_page:
        page = query.paginate(index, items_per_page, False)
        page.curr_num = index
        records = page.items
        
        context['meta']['items'] = ViewUtils.items_for(page)
        context['meta']['pages'] = page.pages
        context['links'] = ViewUtils.get_pagination_urls(
            page,
            'tracker_bp.get_petition_signatures_comparison',
            petition_id=petition_id,
            items=items_per_page
        )
    else:
        records = query.all()
        context['meta']['items'] = {'total': len(records)}

    if not records:
        return context

    record_schema = RecordSchema(exclude=["id"])
    context['signatures'] = [r.signatures_comparison(record_schema, sig_attrs) for r in records]

    return context