import os

class Config(object):

    DEBUG = True

    # default values for db settings table
    DEFAULT_SETTINGS = {
        'poll_petitions_task__interval': os.getenv('POLL_PETITIONS_TASK_INTERVAL'),
        'populate_petitions_task__interval': os.getenv('POPULATE_PETITIONS_TASK_INTERVAL'),
        'test_task__interval': os.getenv('TEST_TASK_INTERVAL'),
    }

    # postgres config
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
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_recycle': 90,
    'pool_timeout': 900,
    'pool_size': 20,
    'max_overflow': 5,
}

    # view and response settings
    JSONIFY_PRETTYPRINT_REGULAR = True

    # log files and settings
    LOG_FILE= os.getenv('LOG_FILE')
    LOG_LEVEL = os.getenv('LOG_LEVEL')

    # CORS config
    CORS_RESOURCE_ORIGINS = os.getenv('CORS_RESOURCE_ORIGINS').split(",")

    # Flask-Compress control settings
    COMPRESS_MIMETYPES = ['application/json']
    COMPRESS_MIN_SIZE = 500
    COMPRESS_LEVEL = 6 # (1 = faster/bigger, 9 = slower/smaller, 6 = default)
    COMPRESS_CACHE_BACKEND = None # may implement redis caching in the future