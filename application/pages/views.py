from flask import render_template, jsonify, current_app
from flask import request, url_for
import requests, json
import datetime as dt
import os

from . import bp

@bp.route('/home', methods=['GET'])
def site_index():
    return render_template('index.html')

@bp.route('/ping', methods=['GET'])
def ping():
    time_now = dt.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    sender = request.args.get('sender')
    response = 'SUCCESS'
    return {
        'response': response,
        'sender': sender,
        'time': time_now
    }