from flask import Flask, render_template
from PetitionTracker import app
from .models import Petition

@app.route('/')
def home():
    
    # user = User.query.get(1)
    context = {'user': 'hi'}
    return render_template('home.html', **context)

# https://github.com/J15t98J/petition-tracker/blob/master/functions/index.js