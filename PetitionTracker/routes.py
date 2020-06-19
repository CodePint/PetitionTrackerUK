from flask import Flask, render_template
from .app import app
from .models import Petition

@app.route('/')
def home():
    pass
    # user = User.query.get(1)
    # context = {'user': user}
    # return render_template('home.html', **context)

# https://github.com/J15t98J/petition-tracker/blob/master/functions/index.js