from flask import render_template, jsonify, current_app
import requests, json
import os

from . import bp

@bp.route('/', methods=['GET'])
def site_index():
    return render_template('index.html')

@bp.route('/make_file/<name>/<content>', methods=['GET'])
def make_file(name, contente):
    breakpoint()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    # make_file()