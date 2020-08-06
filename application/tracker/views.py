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
    SignaturesByCountry,
    SignaturesByCountrySchema,
    SignaturesByRegion,
    SignaturesByRegionSchema,
    SignaturesByConstituency,
    SignaturesByConstituencySchema
)

def get_pagination_urls(pages, function):
    next_url = url_for(function, index=pages.next_num) \
        if pages.has_next else None

    prev_url = url_for(function, index=pages.prev_num) \
        if pages.has_prev else None

    return {'next': next_url, 'prev': prev_url}


@bp.route('/react_flask_test', methods=['GET'])
def react_flask_test():
    now = dt.datetime.now()
    return {'response': 'SUCCESS', 'time': now.strftime("%m/%d/%Y, %H:%M:%S")}


# --- Local Views ---
# Petition Views
@bp.route('/petition/get/', methods=['GET'])
def get_local_petition():
    template_name = 'local/petition.html'
    id = request.args.get('local_id')
    petition = Petition.query.get(id)

    context = {}
    context['id'] = id
    context['petition'] = petition
    context['records'] = petition.ordered_records().limit(10)
    context['latest_record'] = petition.latest_record()
    return render_template(template_name, **context)

@bp.route('/react/petition/get/', methods=['GET'])
def react_get_local_petition():
    id = request.args.get('id')
    petition = Petition.query.get(id)
    records = petition.ordered_records().limit(10).all()
    latest_record = petition.latest_record()

    petition_schema = PetitionSchema()
    records_schema = RecordSchema(many=True)
    record_nested_schema = RecordNestedSchema()

    context = {}
    context['id'] = id
    context['petition'] = petition_schema.dump(petition)
    context['records'] = records_schema.dump(records)
    context['latest_record'] = record_nested_schema.dumps(latest_record)
    return context


@bp.route('/petition/list/', methods=['GET'])
def get_local_list():
    template_name = 'local/index.html'
    items_per_page = 10

    state = request.args.get('state', 'all')
    index = request.args.get('index', 1, type=int)

    if state == 'all':
        query = Petition.get(dynamic=True)
    else:
        query = Petition.get(state=state, dynamic=True)

    pages = query.paginate(index, items_per_page, False)
    page_links = get_pagination_urls(pages, 'tracker_bp.get_local_list')

    context = {}
    context['petitions'] = pages.items
    context['next_url'] = page_links['next']
    context['prev_url'] = page_links['prev']
    context['selected_state'] = state
    context['states'] = list(Petition.STATE_LOOKUP.keys()) + ['all']
    
    return render_template(template_name, **context)

@bp.route('/react/petition/list/', methods=['GET'])
def react_get_local_petition_list():
    items_per_page = 10
    state = request.args.get('state', 'all')
    index = request.args.get('index', 1, type=int)

    if state == 'all':
        query = Petition.get(dynamic=True)
    else:
        query = Petition.get(state=state, dynamic=True)

    pages = query.paginate(index, items_per_page, False)
    page_links = get_pagination_urls(pages, 'tracker_bp.get_local_list')
    petitions_schema = PetitionSchema(many=True)

    context = {}
    context['petitions'] = petitions_schema.dump(pages.items)
    context['next_url'] = page_links['next']
    context['prev_url'] = page_links['prev']
    context['selected_state'] = state
    context['states'] = list(Petition.STATE_LOOKUP.keys()) + ['all']
    
    return context


# Record Views
@bp.route('/petition/<petition_id>/records', methods=['GET'])
def get_record_list(petition_id):
    items_per_page = 10
    template_name = 'local/records/list.html'
    index = request.args.get('index', 1, type=int)

    petition = Petition.query.get(petition_id)
    records = petition.ordered_records()
    latest_record = records.first()

    context = {}
    context['petition'] = petition
    context['records'] = records
    context['latest_record '] = latest_record

    return render_template(template_name, **context)

@bp.route('/react/petition/records/list', methods=['GET'])
def react_get_record_list():
    items_per_page = 10
    index = request.args.get('index', 1, type=int)
    id = request.args.get('id')

    petition = Petition.query.get(id)
    query = petition.ordered_records()
    latest_record = query.first()
    pages = query.paginate(index, items_per_page, False)
    page_links = get_pagination_urls(pages, 'tracker_bp.get_local_list')
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

@bp.route('/petition/<petition_id>/record/<record_id>', methods=['GET'])
def get_record(petition_id, record_id):
    template_name = 'local/records/record.html'

    petition = Petition.query.get(petition_id)
    record = Record.query.get(record_id)

    context = {}
    context['petition'] = petition
    context['record'] = record

    return render_template(template_name, **context)

@bp.route('/react/petition/record/', methods=['GET'])
def react_get_record():
    petition_id = request.args.get('petition_id')
    record_id = request.args.get('record_id')

    petition = Petition.query.get(petition_id)
    record = Record.query.get(record_id)
    petition_schema = PetitionSchema()
    record_nested_schema = RecordNestedSchema()

    context = {}
    context['petition'] = petition_schema.dump(petition)
    context['record'] = record_nested_schema.dump(record)
    
    return context

@bp.route('/petition/<petition_id>/record/<record_id>/signatures/<geography>', methods=['GET'])
def get_signatures_by(petition_id, record_id, geography):
    template_name = 'local/records/signatures.html'

    petition = Petition.query.get(petition_id)
    record = Record.query.get(record_id)

    table, model = record.get_sig_model_attr(geography)

    context = {}
    context['geography'] = geography
    context['petition'] = petition
    context['record'] = record
    context['signatures'] = table.all()

    return render_template(template_name, **context)


# --- Remote Views ---
@bp.route('/petition/remote/list', methods=['GET'])
def fetch_remote_list():
    template_name = 'remote/index.html'
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
    
    return render_template(template_name, **context)


@bp.route('/petition/remote/get', methods=['GET'])
def fetch_remote_petition():
    template_name = 'remote/petition.html'
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
        context['local_petition'] = Petition.query.get(id)
        context['onboarding_in_progress'] = request.args.get('onboarding_in_progress', False)
        context['url'] = response.url
    else:
        context = {'petition': None, 'error': 404, 'id': id}
    
    return render_template(template_name, **context)