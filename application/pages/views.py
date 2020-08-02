from flask import render_template, jsonify, current_app
import requests, json
import os

from . import bp

@bp.route('/', methods=['GET'])
def site_index():
    return render_template('index.html')

# @bp.route('/make_file/<name>/<content>', methods=['GET'])
# def make_file(name, content):
#     directory = 'development/celery'
#     file_path = os.path.join(os.getcwd(), directory, name)
#     SharedTasks.test_task.delay(file_path, content)
#     return 'done'