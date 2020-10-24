from flask import render_template, jsonify, current_app
from flask import request, url_for
import requests, json
import datetime as dt
import os, logging

from . import bp

logger = logging.getLogger(__name__)

@bp.route('/ping', methods=['GET'])
def ping():
    time_now = dt.datetime.now().strftime("%m/%d/%Y, %H:%M:%S")
    sender = request.args.get('sender')
    response = 'SUCCESS'
    logger.info("hello world, from view!")

    return {
        'response': response,
        'sender': sender,
        'time': time_now
    }