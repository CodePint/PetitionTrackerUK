from flask import render_template, jsonify, current_app
import requests, json
from . import bp

@bp.route('/', methods=['GET'])
def site_index():
    return render_template('index.html')

