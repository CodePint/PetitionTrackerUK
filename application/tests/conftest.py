import pytest
import sqlalchemy as sa
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from alembic.command import upgrade
from alembic.config import Config
from faker import Faker
from faker.providers import lorem
from functools import wraps
import os, logging, json

from application.tests.utils import Compose
from application import create_app
from application import db as _db
from application import Config

logger = logging.getLogger(__name__)

Config.load()

TEST_DB_URI = Config.SQLALCHEMY_DATABASE_URI
ALEMBIC_CONFIG = "../../migrations/alembic.ini"

def rkwargs(request):
    return getattr(request, "param", {})

def init_faker():
    faker = Faker()
    faker.add_provider(lorem)
    return faker

def apply_migrations():
    """Applies all alembic migrations."""
    config = Config(ALEMBIC_CONFIG)
    upgrade(config, 'head')

@pytest.fixture(scope="session", autouse=True)
def before_test_run():
    Compose.up()

@pytest.fixture(scope='session')
def app(request):
    """Session-wide test `Flask` application."""
    settings = {}
    settings["TESTING"] = True
    settings["SQLALCHEMY_DATABASE_URI"] = TEST_DB_URI

    # create application, update config, push context
    app = create_app(__name__)
    ctx = app.app_context()
    ctx.push()

    def teardown():
        ctx.pop()

    request.addfinalizer(teardown)
    return app

@pytest.fixture(scope='session')
def db(app, request):
    def teardown():
        _db.drop_all()

    _db.app = app
    _db.create_all()

    request.addfinalizer(teardown)
    return _db


def _session(db, request):
    """Creates a new database session for a test."""
    connection = db.engine.connect()
    transaction = connection.begin()
    options = dict(bind=connection, binds={})
    session = db.create_scoped_session(options=options)

    db.session = session

    def teardown():
        transaction.rollback()
        connection.close()
        session.remove()

    request.addfinalizer(teardown)
    return session

@pytest.fixture(scope="function")
def session(db, request):
    kwargs = rkwargs(request)
    func = kwargs.get("func")
    session = _session(db, request)
    if func: func(session, **kwargs)
    return session

@pytest.fixture(scope="class")
def class_session(db, request):
    kwargs = rkwargs(request)
    func = kwargs.get("func")
    request.cls.session = _session(db, request)
    if func: func(request.cls, **kwargs)
