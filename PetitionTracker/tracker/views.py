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

def get_fetched_index_pagination(current, final):
    range_start = (current - 5) if ((current - 5) > 0 ) else 0
    range_end = (current + 5) if ((current + 5 < final)) else final + 1
    return {'current': current, 'final': final, 'range': [range_start, range_end] }

@bp.route('/petition/fetch/list/', methods=['GET'])
@bp.route('/petition/fetch/list/<state>/', methods=['GET'])
@bp.route('/petition/fetch/list/<state>/<index>', methods=['GET'])
def fetch_index(index=0, state="open"):
    current_index = int(index)
    response = RemotePetition.fetch_list(current_index, state)

    if response.status_code == 200:
        data = response.json()

        petitions = data['data']
        # breakpoint()
        if "?page=" in data['links']['last']:
            final_index = int(data['links']['last'].split("?page=")[1].split("&")[0]) -1

        paginate = get_fetched_index_pagination(current_index, final_index)

        context = {'petitions': petitions, 'paginate': paginate, 'url': response.url}
        return render_template('fetch_list.html', **context)


@bp.route('/petition/fetch/', methods=['GET'])
@bp.route('/petition/fetch/<id>', methods=['GET'])
def fetch_petition(id=None):
    if not id:
        id = request.args.get('id')

    # breakpoint()
    response = RemotePetition.fetch(id)
    http_code = response.status_code

    if http_code == 200:
        data = response.json()
        url = response.url.split(".json")[0]
        context = {'response': http_code, 'petition': data, 'url': url}
    else:
        context = {'response': http_code, 'id': id}
    
    return render_template('fetch_petition.html', **context)


