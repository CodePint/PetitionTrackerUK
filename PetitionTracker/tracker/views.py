from PetitionTracker.tracker import bp
from flask import render_template, current_app

@bp.route('/', methods=['GET'])
def index():
    breakpoint()
    context = {'user': 'user'}
    # breakpoint()
    return render_template('index.html', **context)

@bp.route('/about', methods=['GET'])
def about():
    context = {'user': 'user'}
    return render_template('about.html', **context)
