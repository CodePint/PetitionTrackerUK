from flask import render_template, jsonify, current_app
from flask import request, url_for
import requests, json
from . import bp

from .remote import RemotePetition

from .models import (
    Petition,
    Record,
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency
)

def get_pagination_urls(pages, function):
    next_url = url_for(function, index=pages.next_num) \
        if pages.has_next else None

    prev_url = url_for(function, index=pages.prev_num) \
        if pages.has_prev else None

    return {'next': next_url, 'prev': prev_url}

# --- Local Views ---
# Petition Views
@bp.route('/petition/get/', methods=['GET'])
def get_local_petition():
    template_name = 'local/petition.html'
    id = request.args.get('local_id')
    petition = Petition.query.get(id)

    context = {}
    context['petition'] = petition
    context['records'] = petition.ordered_records().limit(10)
    context['latest_record'] = petition.latest_record()
    return render_template(template_name, **context)

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

# Record Views
@bp.route('/petition/<petition_id>/records', methods=['GET'])
def get_record_list(petition_id):
    template_name = 'local/records/list.html'
    items_per_page = 10

    index = request.args.get('index', 1, type=int)
    
    signature_models = [

    ]
    # breakpoint()
    petition = Petition.query.get(petition_id)
    records = petition.ordered_records()
    latest_record = records.first()

    context = {}
    context['petition'] = petition
    context['records'] = records
    context['latest_record '] = latest_record

    return render_template(template_name, **context)


@bp.route('/petition/<petition_id>/record/<record_id>', methods=['GET'])
def get_record(petition_id, record_id):
    template_name = 'local/records/record.html'

    petition = Petition.query.get(petition_id)
    record = Record.query.get(record_id)

    context = {}
    context['petition'] = petition
    context['record'] = record

    return render_template(template_name, **context)

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

        return render_template(template_name, **context)
    else:
        context['petitions'] = []
        return render_template(template_name, **context)


@bp.route('/petition/remote/get', methods=['GET'])
def fetch_remote_petition(id=None):
    template_name = 'remote/petition.html'
    id = request.args.get('remote_id')

    try:
        response = RemotePetition.get(id)
    except requests.exceptions.HTTPError as e:
        return render_template(template_name, {'error': response.status_code} )

    if response:
        data = response.json()
        url = response.url
        context = {'petition': data, 'url': url}
    else:
        context = {'petition': None, 'error': 404, 'id': id}
    
    return render_template(template_name, **context)