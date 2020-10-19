import logging
import logging.config
from pythonjsonlogger import jsonlogger
from datetime import datetime as dt;

class EFKJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(EFKJsonFormatter, self).add_fields(log_record, record, message_dict)
        log_record['@timestamp'] =  log_record.pop("asctime", dt.now())
        log_record['level'] = log_record.pop("levelname")

# Petition.log(greeting="hello world")