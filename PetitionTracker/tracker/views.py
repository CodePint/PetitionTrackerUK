from flask import render_template, jsonify, current_app
from flask import request
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

def get_fetched_index_pagination(current, data):
    if "?page=" in data['links']['last']:
        final = int(data['links']['last'].split("?page=")[1].split("&")[0]) -1
    else:
        final = 0
    
    range_start = (current - 5) if ((current - 5) > 0 ) else 0
    range_end = (current + 5) if ((current + 5 < final)) else final + 1
    return {'current': current, 'final': final, 'range': [range_start, range_end] }

@bp.route('/petition/fetch/list/', methods=['GET'])
@bp.route('/petition/fetch/list/<index>', methods=['GET'])
def fetch_remote_list(index=0):
    current_index = int(index)
    state = request.args.get('state', 'all')
    response = RemotePetition.fetch_list(current_index, state)

    try: 
        response = RemotePetition.fetch_list(current_index, state)
    except requests.exceptions.HTTPError as e: 
        return render_template('fetch_list.html', {'error': response.status_code} )

    data = response.json()
    petitions = data['data']

    if petitions:
        context = {}
        context['petitions'] = petitions
        context['paginate'] = get_fetched_index_pagination(current_index, data)
        context['states'] = RemotePetition.list_states()
        context['selected_state'] = state

        return render_template('fetch_list.html', **context)
    else:
        return render_template('fetch_list.html', {'petitions': [] })


@bp.route('/petition/fetch/', methods=['GET'])
@bp.route('/petition/fetch/<id>', methods=['GET'])
def fetch_remote_petition(id=None):
    if not id:
        id = request.args.get('id')

    try: 
        response = RemotePetition.fetch(id)
    except requests.exceptions.HTTPError as e: 
        return render_template('fetch_petition.html', {'error': response.status_code} )

    if response:
        data = response.json()
        url = response.url.split(".json")[0]
        context = {'petition': data, 'url': url}
    else:
        context = {'error': 404, 'id': id}
    
    return render_template('fetch_petition.html', **context)


