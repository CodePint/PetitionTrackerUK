from flask import current_app
from functools import wraps
from datetime import datetime as dt
import pdb
def with_logging(level="INFO"):

    def truncate_arg(val):
        if len(str(val)) > 100:
            return str(val)[:50] + "..." + str(val)[-50:]
        else:
            return(str(val))
    
    def wrapper(func):
        @wraps(func)
        def setup_logger(*args, **kwargs):
            from application.models import Logger
            
            logger = kwargs.pop("logger", Logger())
            logger.kwargs.update({"module": func.__qualname__})

            func_log_kwargs = str({k: truncate_arg(v) for k, v in kwargs.items()})
            logger.func_log(name=func.__name__, level=level, kwargs=func_log_kwargs)
            kwargs["logger"] = logger

            return func(*args, **kwargs)
        return setup_logger
    return wrapper

    
def will_save_log(func):

    @wraps(func)
    def check_level(*args, **kwargs):
        from application.models import Logger

        force_save = kwargs.get('save')
        if not force_save:
            LOG_LEVEL = current_app.config.get("DB_LOG_LEVEL", "DEBUG")
            func_level = int(Logger.LEVELS[kwargs["level"]])
            logger_level = int(Logger.LEVELS[LOG_LEVEL])
            kwargs["save"] = func_level >= logger_level
        
        return func(*args, **kwargs)
    return check_level
