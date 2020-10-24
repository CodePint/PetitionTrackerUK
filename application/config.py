import os
from dotenv import load_dotenv

# application config object
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
        cls.FLASK_ENV = ENV.get("FLASK_ENV", else_raise=True)
        cls.FLASK_ENV_FILE = cls.CONFIG_FILES.get(cls.FLASK_ENV)

        if cls.FLASK_ENV_FILE:
            print("FLASK_ENV: {}".format(cls.FLASK_ENV))
        else:
            raise RuntimeError("INAVLID FLASK ENV: '{}'".format(cls.FLASK_ENV))

        load_dotenv(dotenv_path=cls.FLASK_ENV_FILE, override=True)

    @classmethod
    def override_env(cls):
        cls.ENV_OVERRIDES = ENV.get("OVERRIDES", type=ENV.to_list)
        print("ENV_OVERRIDES: {}".format(cls.ENV_OVERRIDES))

        [load_dotenv(dotenv_path=env, override=True ) for env in cls.ENV_OVERRIDES]

    @classmethod
    def import_env(cls):
        cls.DEBUG = ENV.get("FLASK_DEBUG", type=ENV.to_bool)

        # default values for Setting table
        cls.DEFAULT_SETTINGS = {
            "signatures_threshold": ENV.get("SIGNATURES_THRESHOLD"),
            "trending_threshold": ENV.get("TRENDING_THRESHOLD")
        }

        # postgres config
        cls.POSTGRES_TEMPLATE = "postgresql://%(user)s:%(pw)s@%(host)s:%(port)s/%(db)s"
        cls.POSTGRES_CONFIG = {
            "user": ENV.get("POSTGRES_USER", else_raise=True),
            "pw": ENV.get("POSTGRES_PASSWORD", else_raise=True),
            "db": ENV.get("POSTGRES_DB", else_raise=True),
            "host": ENV.get("POSTGRES_HOST", else_raise=True),
            "port": ENV.get("POSTGRES_PORT", else_raise=True)
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

        # cls.REDIS_URI = ENV.get("REDIS_URI", else_raise=True)
        # cls.CELERY_TIMEZONE = ENV.get("TIMEZONE", fallback="Europe/London")
        # cls.CELERY_ENABLE_UTC = ENV.get("CELERY_ENABLE_UTC", fallback=True)
        # cls.CELERY_DEFAULT_QUEUE = ENV.get("DEFAULT_QUEUE", fallback="application")
        # cls.CELERY_ONCE_TIMEOUT = ENV.get("CELERY_ONCE_TIMEOUT", fallback=60 * 60)
        # cls.CELERY_ONCE_BLOCKING = ENV.get("CELERY_ONCE_BLOCKING", fallback=False)
        # cls.CELERY_ONCE_BLOCKING_TIMEOUT = ENV.get("CELERY_ONCE_BLOCKING_TIMEOUT", fallback=0)

        # view and response settings
        cls.JSONIFY_PRETTYPRINT_REGULAR = True
        cls.CORS_ORIGINS = ENV.get("CORS_ORIGINS", fallback='', type=ENV.to_list)

        # log files and settings
        cls.LOG_FILE = ENV.get("LOG_FILE")
        cls.LOG_LEVEL = ENV.get("LOG_LEVEL", else_raise=True)
        cls.DB_LOG_LEVEL = ENV.get("DB_LOG_LEVEL", else_raise=True)

        # Flask-Compress control settings
        cls.COMPRESS_MIMETYPES = ["application/json"]
        cls.COMPRESS_MIN_SIZE = 500
        cls.COMPRESS_LEVEL = 6 # (1 = faster/bigger, 9 = slower/smaller, 6 = default)
        cls.COMPRESS_CACHE_BACKEND = None # may implement redis caching in the future



# Enviroment loader helper
class ENV():

    @classmethod
    def raiser(cls, ex, msg):
        raise ex(msg)

    @classmethod
    def to_bool(cls, var):
        return var.upper() == "TRUE"

    @classmethod
    def to_list(cls, var):
        return var.strip("[]").replace(", ", ",") .split(",")

    @classmethod
    def get(cls, key, fallback=None, type=str, else_raise=False, ex=RuntimeError, msg="NOT FOUND"):
        handle = lambda: cls.raiser(ex, "{}: {}".format(key, msg)) if else_raise else fallback
        value = os.getenv(key)
        return type(value) if value else handle()