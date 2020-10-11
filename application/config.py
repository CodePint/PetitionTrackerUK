import os
from dotenv import load_dotenv

def to_bool(var):
    return var.upper() == "TRUE"

def to_list(var):
    return var.split(",")

def getenv(var, type=str):
    var = os.getenv(var)
    return type(var) if var else None

class Config(object):

    @classmethod
    def init_env(cls):
        load_dotenv(dotenv_path=base_env_file, override=True)
        cls.FLASK_ENV = os.getenv('FLASK_ENV')
        cls.BASE_ENV_FILE = ".base.env"

        print("LOADING FLASK_ENV: {}".format(cls.FLASK_ENV))
        if cls.FLASK_ENV == "development":
            cls.DOCKER_ENV = getenv('DOCKER_ENV', type=to_bool)
            if cls.DOCKER_ENV:
                print("USING DOCKER DEV ENV")
                env_file = ".docker.dev.env"
            else:
                env_file = ".dev.env"
        elif cls.FLASK_ENV == "production":
            env_file = ".prod.env"
        elif cls.FLASK_ENV == "testing":
            env_file = ".test.env"
        
        cls.FLASK_ENV_FILE = env_file
        return load_dotenv(dotenv_path=cls.FLASK_ENV_FILE, override=True)

    @classmethod
    def import_env(cls):
        cls.DEBUG = getenv('FLASK_DEBUG', type=to_bool)

        # default values for Setting table
        cls.DEFAULT_SETTINGS = {
            'signatures_threshold': getenv('SIGNATURES_THRESHOLD'),
            'trending_threshold': getenv('TRENDING_THRESHOLD')
        }

        # default values for Task table
        cls.PERIODIC_TASK_SETTINGS = [
            {
                "name": "poll_total_sigs_task",
                "interval":getenv('POLL_TOTAL_SIGS_TASK_INTERVAL', type=int),
                "enabled": getenv('POLL_TOTAL_SIGS_TASK', type=to_bool),
                "run_on_startup":  getenv('POLL_TOTAL_SIGS_TASK_ON_STARTUP', type=to_bool)
            },
            {
                "name": "poll_geographic_sigs_task",
                "interval": getenv('POLL_GEOGRAPHIC_SIGS_TASK_INTERVAL', type=int),
                "enabled": getenv('POLL_GEOGRAPHIC_SIGS_TASK', type=to_bool),
                "run_on_startup":  getenv('POLL_GEOGRAPHIC_SIGS_TASK_ON_STARTUP', type=to_bool)

            },
            {
                "name": "poll_trending_geographic_sigs_task",
                "interval": getenv('POLL_TRENDING_GEOGRAPHIC_SIGS_TASK_INTERVAL', type=int),
                "enabled": getenv('POLL_TRENDING_GEOGRAPHIC_SIGS_TASK', type=to_bool),
                "run_on_startup":  getenv('POLL_TRENDING_GEOGRAPHIC_SIGS_TASK_ON_STARTUP', type=to_bool)

            },
            {
                "name": "populate_petitions_task",
                "interval": getenv('POPULATE_PETITIONS_TASK_INTERVAL', type=int),
                "enabled": getenv('POPULATE_PETITIONS_TASK', type=to_bool),
                "run_on_startup":  getenv('POPULATE_PETITIONS_TASK_ON_STARTUP', type=to_bool)

            },
                {
                "name": "update_trending_petitions_pos_task",
                "interval": getenv('UPDATE_TRENDING_PETITION_POS_TASK_INTERVAL', type=int),
                "enabled": getenv('UPDATE_TRENDING_PETITION_POS_TASK', type=to_bool),
                "run_on_startup":  getenv('UPDATE_TRENDING_PETITION_POS_TASK_ON_STARTUP', type=to_bool)

            },
                {
                "name": "test_task",
                "interval":getenv('TEST_TASK_INTERVAL', type=int),
                "enabled": getenv('TEST_TASK', type=to_bool),
                "run_on_startup":  getenv('TEST_TASK_ON_STARTUP', type=to_bool)

            },
        ]

        # postgres config
        cls.POSTGRES_TEMPLATE = 'postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s'
        cls.POSTGRES_CONFIG = {
            'user': getenv('POSTGRES_USER'),
            'pw': getenv('POSTGRES_PASSWORD'), 
            'db': getenv('POSTGRES_DB'),
            'host': getenv('POSTGRES_HOST'),
            'port': getenv('POSTGRES_PORT')
        }

        cls.SQLALCHEMY_DATABASE_URI = cls.POSTGRES_TEMPLATE % cls.POSTGRES_CONFIG
        cls.SQLALCHEMY_TRACK_MODIFICATIONS = False
        cls.SQLALCHEMY_ECHO = cls.DEBUG
        cls.SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_recycle': 90,
            'pool_timeout': 900,
            'pool_size': 8,
            'max_overflow': 5,
        }

        # view and response settings
        cls.JSONIFY_PRETTYPRINT_REGULAR = True

        # log files and settings
        cls.LOG_FILE= getenv('LOG_FILE')
        cls.LOG_LEVEL = getenv('LOG_LEVEL')
        cls.DB_LOG_LEVEL= getenv('DB_LOG_LEVEL')
        
        # CORS config
        cls.CORS_RESOURCE_ORIGINS = getenv('CORS_RESOURCE_ORIGINS', to_list)

        # Flask-Compress control settings
        cls.COMPRESS_MIMETYPES = ['application/json']
        cls.COMPRESS_MIN_SIZE = 500
        cls.COMPRESS_LEVEL = 6 # (1 = faster/bigger, 9 = slower/smaller, 6 = default)
        cls.COMPRESS_CACHE_BACKEND = None # may implement redis caching in the future