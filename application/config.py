import os
from dotenv import load_dotenv


class Config(object):

    CONFIG_FILES = {
        "development": ".dev.env",
        "production": ".prod.env",
        "testing": ".test.env",
    }
    
    @classmethod
    def init(cls):
        Config.init_env()
        Config.override_env()
        Config.import_env()

    @classmethod
    def init_env(cls):
        load_dotenv(dotenv_path=".env", override=True)
        cls.FLASK_ENV = getenv("FLASK_ENV", else_raise=True)
        cls.FLASK_ENV_FILE = cls.CONFIG_FILES.get(cls.FLASK_ENV)

        if cls.FLASK_ENV_FILE:
            print("FLASK_ENV: {}".format(cls.FLASK_ENV))
        else:
            raise RuntimeError("INAVLID FLASK ENV: '{}'".format(cls.FLASK_ENV))

        load_dotenv(dotenv_path=cls.FLASK_ENV_FILE, override=True)

    @classmethod
    def override_env(cls):
        cls.ENV_OVERRIDES = getenv("OVERRIDES", type=to_list)
        print("ENV_OVERRIDES: {}".format(cls.ENV_OVERRIDES))

        [load_dotenv(dotenv_path=env, override=True ) for env in cls.ENV_OVERRIDES]

    @classmethod
    def import_env(cls):
        cls.DEBUG = getenv("FLASK_DEBUG", type=to_bool)

        # default values for Setting table
        cls.DEFAULT_SETTINGS = {
            "signatures_threshold": getenv("SIGNATURES_THRESHOLD"),
            "trending_threshold": getenv("TRENDING_THRESHOLD")
        }

        # default values for Task table
        cls.PERIODIC_TASK_SETTINGS = [
            {
                "name": "poll_total_sigs_task",
                "interval":getenv("POLL_TOTAL_SIGS_TASK_INTERVAL", type=int),
                "enabled": getenv("POLL_TOTAL_SIGS_TASK", type=to_bool),
                "run_on_startup":  getenv("POLL_TOTAL_SIGS_TASK_ON_STARTUP", type=to_bool)
            },
            {
                "name": "poll_geographic_sigs_task",
                "interval": getenv("POLL_GEOGRAPHIC_SIGS_TASK_INTERVAL", type=int),
                "enabled": getenv("POLL_GEOGRAPHIC_SIGS_TASK", type=to_bool),
                "run_on_startup":  getenv("POLL_GEOGRAPHIC_SIGS_TASK_ON_STARTUP", type=to_bool)

            },
            {
                "name": "poll_trending_geographic_sigs_task",
                "interval": getenv("POLL_TRENDING_GEOGRAPHIC_SIGS_TASK_INTERVAL", type=int),
                "enabled": getenv("POLL_TRENDING_GEOGRAPHIC_SIGS_TASK", type=to_bool),
                "run_on_startup":  getenv("POLL_TRENDING_GEOGRAPHIC_SIGS_TASK_ON_STARTUP", type=to_bool)

            },
            {
                "name": "populate_petitions_task",
                "interval": getenv("POPULATE_PETITIONS_TASK_INTERVAL", type=int),
                "enabled": getenv("POPULATE_PETITIONS_TASK", type=to_bool),
                "run_on_startup":  getenv("POPULATE_PETITIONS_TASK_ON_STARTUP", type=to_bool)

            },
                {
                "name": "update_trending_petitions_pos_task",
                "interval": getenv("UPDATE_TRENDING_PETITION_POS_TASK_INTERVAL", type=int),
                "enabled": getenv("UPDATE_TRENDING_PETITION_POS_TASK", type=to_bool),
                "run_on_startup":  getenv("UPDATE_TRENDING_PETITION_POS_TASK_ON_STARTUP", type=to_bool)

            },
                {
                "name": "test_task",
                "interval":getenv("TEST_TASK_INTERVAL", type=int),
                "enabled": getenv("TEST_TASK", type=to_bool),
                "run_on_startup":  getenv("TEST_TASK_ON_STARTUP", type=to_bool)

            },
        ]

        # postgres config
        cls.POSTGRES_TEMPLATE = "postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s"
        cls.POSTGRES_CONFIG = {
            "user": getenv("POSTGRES_USER", else_raise=True),
            "pw": getenv("POSTGRES_PASSWORD", else_raise=True), 
            "db": getenv("POSTGRES_DB", else_raise=True),
            "host": getenv("POSTGRES_HOST", else_raise=True),
            "port": getenv("POSTGRES_PORT", else_raise=True)
        }

        cls.SQLALCHEMY_DATABASE_URI = cls.POSTGRES_TEMPLATE % cls.POSTGRES_CONFIG
        cls.SQLALCHEMY_TRACK_MODIFICATIONS = False
        cls.SQLALCHEMY_ECHO = cls.DEBUG
        cls.SQLALCHEMY_ENGINE_OPTIONS = {
            "pool_recycle": 90,
            "pool_timeout": 900,
            "pool_size": 8,
            "max_overflow": 5,
        }

        # view and response settings
        cls.JSONIFY_PRETTYPRINT_REGULAR = True
        cls.CORS_ORIGINS = getenv("CORS_ORIGINS", fallback='', type=to_list)
        # log files and settings
        cls.LOG_FILE = getenv("LOG_FILE")
        cls.LOG_LEVEL = getenv("LOG_LEVEL", else_raise=True)
        cls.DB_LOG_LEVEL = getenv("DB_LOG_LEVEL", else_raise=True)
        
        # Flask-Compress control settings
        cls.COMPRESS_MIMETYPES = ["application/json"]
        cls.COMPRESS_MIN_SIZE = 500
        cls.COMPRESS_LEVEL = 6 # (1 = faster/bigger, 9 = slower/smaller, 6 = default)
        cls.COMPRESS_CACHE_BACKEND = None # may implement redis caching in the future


## Config Helper Functions ##
def raiser(ex, msg): 
    raise ex(msg)

def to_bool(var):
    return var.upper() == "TRUE"

def to_list(var):
    return var.strip("[]").replace(", ", ",") .split(",")

def getenv(key, fallback=None, type=str, else_raise=False, ex=RuntimeError, msg="NOT FOUND"):
    handle = lambda: raiser(ex, "{}: {}".format(key, msg)) if else_raise else fallback
    value = os.getenv(key)
    return type(value) if value else handle()