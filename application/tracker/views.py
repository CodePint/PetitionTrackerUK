from flask import render_template, redirect, url_for, jsonify, current_app
from flask import request, url_for
import requests, json, os
import datetime as dt

from . import bp
from .remote import RemotePetition

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
    SignaturesByConstituencySchema
)

def get_pagination_urls(pages, function, **url_kwargs):
    next_url = url_for(function, **url_kwargs) \
        if pages.has_next else None

    prev_url = url_for(function, **url_kwargs) \
        if pages.has_prev else None

    return {'next': next_url, 'prev': prev_url}

def select_records(petition, time_period):
    time_range = dt.datetime.now() - dt.timedelta(**time_period)
    records = petition.records.filter(Record.timestamp > time_range)

@bp.route('/petition/<id>', methods=['GET'])
def get_petition(id):
    time_ago = request.args.get('time_ago', {}, type=json.loads)
    petition = Petition.query.get(id)
    latest_record = petition.latest_record()

    if time_ago.get('all'):
        records = petition.ordered_records().all()
    else:
        records = petition.records_since(time_ago).all()


    petition_schema = PetitionSchema()
    records_schema = RecordSchema(many=True)
    record_nested_schema = RecordNestedSchema()

    context = {}
    context['id'] = id
    context['petition'] = petition_schema.dump(petition)
    context['records'] = records_schema.dump(records)
    context['latest_record'] = record_nested_schema.dumps(latest_record)
    return context

@bp.route('/petitions', methods=['GET'])
def get_petitions():
    items_per_page = 10
    state = request.args.get('state', 'all')
    index = request.args.get('index', 1, type=int)

    if state == 'all':
        query = Petition.get(dynamic=True)
    else:
        query = Petition.get(state=state, dynamic=True)

    pages = query.paginate(index, items_per_page, False)
    page_links = get_pagination_urls(pages, 'tracker_bp.get_petitions', state=state)
    petitions_schema = PetitionSchema(many=True)

    context = {}
    context['petitions'] = petitions_schema.dump(pages.items)
    context['next_url'] = page_links['next']
    context['prev_url'] = page_links['prev']
    context['selected_state'] = state
    context['states'] = list(Petition.STATE_LOOKUP.keys()) + ['all']
    
    return context

@bp.route('/petition/<petition_id>/record/<record_id>', methods=['GET'])
def get_record(petition_id, record_id):
    petition = Petition.query.get(petition_id)
    record = Record.query.get(record_id)
    petition_schema = PetitionSchema()
    record_nested_schema = RecordNestedSchema()

    context = {}
    context['petition'] = petition_schema.dump(petition)
    context['record'] = record_nested_schema.dump(record)
    
    return context

@bp.route('/petition/<petition_id>/records', methods=['GET'])
def get_records(petition_id):
    items_per_page = 10
    index = request.args.get('index', 1, type=int)

    petition = Petition.query.get(petition_id)
    query = petition.ordered_records()
    latest_record = query.first()
    pages = query.paginate(index, items_per_page, False)
    page_links = get_pagination_urls(pages, 'tracker_bp.get_records', petition_id=petition_id)
    records = pages.items

    petition_schema = PetitionSchema()
    records_schema = RecordSchema(many=True)
    record_nested_schema = RecordNestedSchema()

    context = {}
    context['next_url'] = page_links['next']
    context['prev_url'] = page_links['prev']
    context['records'] = records_schema.dumps(pages.items)
    context['petition'] = petition_schema.dumps(petition)
    context['latest_record '] = record_nested_schema.dump(latest_record)

    return context

@bp.route('/petition/<petition_id>/record/<record_id>/signatures/<geography>', methods=['GET'])
def get_signatures_by(petition_id, record_id, geography):
    petition = Petition.query.get(petition_id)
    record = Record.query.get(record_id)
    table, model = record.get_sig_model_attr(geography)
    signatures = table.all()

    signatures_schema_class = SignaturesBySchema.get_schema_for(model)
    signatures_schema = signatures_schema_class(many=True)
    petition_schema = PetitionSchema()
    record_schema = RecordSchema()

    context = {}
    context['geography'] = geography
    context['petition'] = petition_schema.dumps(petition)
    context['record'] = record_schema.dumps(record)
    context['signatures'] = signatures_schema.dumps(table.all())

    return context

# remote views
# untested since react migration, may still be used
@bp.route('/remote/petitions/<petition_id>', methods=['GET'])
def fetch_remote_petition(petition_id):
    id = request.args.get('remote_id')

    try:
        response = RemotePetition.get(id)
    except requests.exceptions.HTTPError as e:
        return render_template(template_name, {'error': response.status_code} )

    if response:
        data = response.json()
        context = {}
        context['id'] = id
        context['petition'] = response.json()
        context['local_petition'] = Petition.query.get(petition_id)
        context['onboarding_in_progress'] = request.args.get('onboarding_in_progress', False)
        context['url'] = response.url
    else:
        context = {'petition': None, 'error': 404, 'petition_id': petition_id}
    
    return context

@bp.route('/remote/petitions', methods=['GET'])
def fetch_remote_petitions():
    current_index = int(request.args.get('index', '1'))
    state = request.args.get('state', 'all')
    response = RemotePetition.get_page(current_index, state)

    try: 
        response = RemotePetition.get_page(index=current_index, state=state)
        data = response.json()
        petitions = data['data']
    except requests.exceptions.HTTPError as e: 
        return render_template(template_name, {'error': response.status_code} )

    context = {}
    context['states'] = RemotePetition.list_states
    context['url'] = response.url
    if petitions:
        context['petitions'] = petitions
        context['paginate'] = RemotePetition.get_fetched_index_pagination(current_index, data)
        context['selected_state'] = state
    else:
        context['petitions'] = []
    
    return context
