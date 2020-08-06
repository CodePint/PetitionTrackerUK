import os

class Config(object):

    POSTGRES_TEMPLATE = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s'
    POSTGRES_CONFIG = {
        'user': 'petitionadmin',
        'pw': 'new_password',
        'db': 'petitiondb',
        'host': 'localhost',
        'port': '5432',
    }
    
    SQLALCHEMY_DATABASE_URI = POSTGRES_TEMPLATE % POSTGRES_CONFIG
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSONIFY_PRETTYPRINT_REGULAR = True
    DEBUG = True

    LOG_FILE= os.getenv('LOG_FILE')
    LOG_LEVEL = os.getenv('LOG_LEVEL')

    CORS_RESOURCE_ORIGINS = os.getenv('CORS_RESOURCE_ORIGINS').split(",")

    DEFAULT_SETTINGS = {
        'poll_petitions_task__interval': os.getenv('POLL_PETITIONS_TASK_INTERVAL'),
        'populate_petitions_task__interval': os.getenv('POPULATE_PETITIONS_TASK_INTERVAL'),
        'test_task__interval': os.getenv('TEST_TASK_INTERVAL'),
    }