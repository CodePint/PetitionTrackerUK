from flask import Flask, Blueprint, render_template

bp = Blueprint(
    'tracker_bp', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/tracker/static'
)

from PetitionTracker.tracker import views