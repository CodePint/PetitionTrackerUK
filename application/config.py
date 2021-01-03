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
    def load(cls):
        Config.init_env()
        Config.override_env()
        CeleryConfig.import_env()
        Config.import_env()
        return cls

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
        cls.ENV_OVERRIDES = ENV.get("OVERRIDES", type=ENV.to_list, fallback=[])
        print("ENV_OVERRIDES: {}".format(cls.ENV_OVERRIDES))
        [load_dotenv(dotenv_path=env, override=True) for env in cls.ENV_OVERRIDES]

    @classmethod
    def import_env(cls):
        cls.DEBUG = ENV.get("FLASK_DEBUG", type=ENV.to_bool)

        # default values for Setting table
        cls.DEFAULT_SETTINGS = {
            "signatures_threshold": ENV.get("SIGNATURES_THRESHOLD"),
            "trending_threshold": ENV.get("TRENDING_THRESHOLD")
        }
        cls.PROJ_SCRIPTS_DIR = ENV.get("PROJ_SCRIPTS_DIR", fallback="./scripts")

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

        # Redis config
        cls.REDIS_HOST = ENV.get("REDIS_HOST", else_raise=True)
        cls.REDIS_PORT = ENV.get("REDIS_PORT", else_raise=True)
        cls.REDIS_BROKER = f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}/0"

        # shared celery config
        cls.CELERY_MAX_RETRY_COUNTDOWN = ENV.get("CELERY_MAX_RETRY_COUNTDOWN", fallback=300)
        cls.CELERY_ONCE_DEFAULT_TIMEOUT = ENV.get("CELERY_ONCE_DEFAULT_TIMEOUT", fallback=60 * 60)
        cls.CELERY_CONFIG = CeleryConfig

        # view and response settings
        cls.JSONIFY_PRETTYPRINT_REGULAR = True
        cls.CORS_ORIGINS = ENV.get("CORS_ORIGINS", fallback='*', type=ENV.to_list)

        # log files and settings
        cls.LOG_FILE = ENV.get("LOG_FILE")
        cls.LOG_LEVEL = ENV.get("LOG_LEVEL", else_raise=True)

        # Flask-Compress control settings
        cls.COMPRESS_MIMETYPES = ["application/json"]
        cls.COMPRESS_MIN_SIZE = 500
        cls.COMPRESS_LEVEL = 6 # (1 = faster/bigger, 9 = slower/smaller, 6 = default)
        cls.COMPRESS_CACHE_BACKEND = None # may implement redis caching in the future



class CeleryConfig(object):

    @classmethod
    def import_env(cls):
        cls.REDIS_HOST = ENV.get("REDIS_HOST", else_raise=True)
        cls.REDIS_PORT = ENV.get("REDIS_PORT", else_raise=True)
        cls.REDIS_BROKER = f"redis://{cls.REDIS_HOST}:{cls.REDIS_PORT}/0"

        cls.CELERY_TIMEZONE = ENV.get("CELERY_TIMEZONE", fallback="Europe/London")
        cls.CELERY_DEFAULT_QUEUE = ENV.get("CELERY_DEFAULT_QUEUE", fallback="application")
        cls.CELERY_MAX_RETRY_COUNTDOWN = ENV.get("CELERY_MAX_RETRY_COUNTDOWN", fallback=300)
        cls.CELERY_ONCE_DEFAULT_TIMEOUT = ENV.get("CELERY_ONCE_DEFAULT_TIMEOUT", fallback=60 * 60)

        cls.BASE = {
            "timezone": cls.CELERY_TIMEZONE,
            "task_default_queue": cls.CELERY_DEFAULT_QUEUE,
        }

        cls.ONCE = {
            "backend": "celery_once.backends.Redis",
            "settings": {
                "url": cls.REDIS_BROKER,
                "default_timout": cls.CELERY_ONCE_DEFAULT_TIMEOUT
            }
        }

        cls.REDBEAT = {
            "redbeat_redis_url": cls.REDIS_BROKER,
            "redbeat_lock_key": None
        }


class EnvVarNotFound(ValueError):
    def __init__(self, key):
        self.message = key


# Enviroment loader helper
class ENV():

    @classmethod
    def raiser(cls, ex, msg, **kwargs):
        raise ex(msg, **kwargs)

    @classmethod
    def to_bool(cls, var):
        return var.upper() == "TRUE"

    @classmethod
    def to_list(cls, var):
        return var.strip("[]").replace(", ", ",") .split(",")

    @classmethod
    def get(cls, key, fallback=None, type=str, else_raise=False, msg="NOT FOUND"):
        handle = lambda: cls.raiser(EnvVarNotFound, key) if else_raise else fallback
        value = os.getenv(key)
        return type(value) if value else handle()

