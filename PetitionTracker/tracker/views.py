from flask import render_template, jsonify, current_app
import requests, json

from . import bp
from .models import (
    Petition,
    Record,
    SignaturesByCountry,
    SignaturesByRegion,
    SignaturesByConstituency
)

@bp.route('/', methods=['GET'])
def index():
    breakpoint()
    context = {'user': 'user'}
    return render_template('index.html', **context)

@bp.route('/petition/<id>', methods=['GET'])
def fetch_petition(id):
    url = Petition.BASE_URL + id + '.json'
    response = requests.get(url)
    http_code = response.status_code
    if http_code == 200:
        petition_data = response.json()
        context = {'petition': petition_data}
        return render_template('petition.html', **context)
    else:
        context = {'error': http_code}
        return render_template('petition.html', **context)

