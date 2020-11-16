import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import os, logging, json, pytest

from application.tests.conftest import app, db, session

@pytest.fixture(scope="class")
def tracker_model_seeds(app, db, session):
    '''creates seed data for tracker models'''
