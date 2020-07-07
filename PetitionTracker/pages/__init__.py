from flask import Flask, Blueprint, render_template

bp = Blueprint(
    'pages_bp', __name__,
    template_folder='templates',
    static_folder='static',
    static_url_path='/pages/static'
)

from . import views