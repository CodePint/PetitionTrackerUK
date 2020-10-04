import os
ENV_FILE = '.env'
from dotenv import load_dotenv
load_dotenv(dotenv_path=ENV_FILE, override=True)

def to_bool(var):
    return var.upper() == "TRUE"

class Config(object):

    @classmethod
    def set_env(cls, env="development", overide=True):
        if env == "development":
            env_file = ".dev.env"
        elif env == "production":
            env_file = ".prod.env"
        elif env == "testing":
            env_file = ".test.env"
        
        cls.FLASK_ENV_FILE = env_file
        return load_dotenv(dotenv_path=cls.FLASK_ENV_FILE, override=overide)

    DEBUG = os.get_env('FLASK_DEBUG')

    # default values for Setting table
    DEFAULT_SETTINGS = {
        'signatures_threshold': os.getenv('SIGNATURES_THRESHOLD'),
        'trending_threshold': os.getenv('TRENDING_THRESHOLD')
    }

    # default values for Task table
    PERIODIC_TASK_SETTINGS = [
        {
            "name": "poll_total_sigs_task",
            "interval": int(os.getenv('POLL_TOTAL_SIGS_TASK_INTERVAL')),
            "enabled": to_bool(os.getenv('POLL_TOTAL_SIGS_TASK'))
        },
        {
            "name": "poll_geographic_sigs_task",
            "interval": int(os.getenv('POLL_GEOGRAPHIC_SIGS_TASK_INTERVAL')),
            "enabled": to_bool(os.getenv('POLL_GEOGRAPHIC_SIGS_TASK'))
        },
        {
            "name": "poll_trending_geographic_sigs_task",
            "interval": int(os.getenv('POLL_TRENDING_GEOGRAPHIC_SIGS_TASK_INTERVAL')),
            "enabled": to_bool(os.getenv('POLL_TRENDING_GEOGRAPHIC_SIGS_TASK'))
        },
        {
            "name": "populate_petitions_task",
            "interval": int(os.getenv('POPULATE_PETITIONS_TASK_INTERVAL')),
            "enabled": to_bool(os.getenv('POPULATE_PETITIONS_TASK'))
        },
            {
            "name": "update_trending_petitions_pos_task",
            "interval": int(os.getenv('UPDATE_TRENDING_PETITION_POS_TASK_INTERVAL')),
            "enabled": to_bool(os.getenv('UPDATE_TRENDING_PETITION_POS_TASK'))
        },
            {
            "name": "test_task",
            "interval":int(os.getenv('TEST_TASK_INTERVAL')),
            "enabled": to_bool(os.getenv('TEST_TASK'))
        },
    ]

    # postgres config
    POSTGRES_TEMPLATE = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s'
    POSTGRES_CONFIG = {
        'user': os.getenv('POSTGRES_USER'),
        'pw': os.getenv('POSTGRES_PASSWORD'), 
        'db': os.getenv('POSTGRES_DB'),
        'host': os.getenv('POSTGRES_HOST'),
        'port': os.getenv('POSTGRES_PORT')
    }
    SQLALCHEMY_DATABASE_URI = POSTGRES_TEMPLATE % POSTGRES_CONFIG
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 90,
        'pool_timeout': 900,
        'pool_size': 8,
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