from flask import Flask, Blueprint, render_template
from flask import current_app as app
from .models import Petition

# tracke blueprint config
tracker_bp = Blueprint(
    'tracker_bp', __name__,
    template_folder='templates',
    static_folder='static'
)

@tracker_bp.route('/', methods=['GET'])
def home():
    context = {'user': 'user'}
    return render_template('home.html', **context)

# https://github.com/J15t98J/petition-tracker/blob/master/functions/index.js