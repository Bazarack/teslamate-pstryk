import logging
from logging.handlers import RotatingFileHandler
import os
from datetime import datetime
from zoneinfo import ZoneInfo

class TimeFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, ZoneInfo("Europe/Warsaw"))
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

log_file = os.path.join(os.path.dirname(__file__), 'logger.log')
#os.makedirs(os.path.dirname(log_file), exist_ok=True)

logger = logging.getLogger("pstrykmate")
logger.setLevel(logging.DEBUG)

handler = RotatingFileHandler(log_file, maxBytes=5_000_000, backupCount=10)
formatter = TimeFormatter('%(asctime)s [%(levelname)s] %(message)s', datefmt="%Y-%m-%d %H:%M:%S")
handler.setFormatter(formatter)

if not logger.hasHandlers():
    logger.addHandler(handler)