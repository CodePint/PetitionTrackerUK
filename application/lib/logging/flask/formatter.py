import logging
import logging.config
from pythonjsonlogger import jsonlogger
from datetime import datetime as dt

class EFKJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(EFKJsonFormatter, self).add_fields(log_record, record, message_dict)
        timestamp  = self.fmt_ts(ts=log_record.pop("asctime"), ms=log_record.pop("msecs"))
        log_record["timestamp"] = timestamp
        log_record["level"] = log_record.pop("levelname")
        return log_record

    def fmt_ts(self, ts, ms, dp=3):
        return ts + "." + str(ms).split(".")[1][:dp]
