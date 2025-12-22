import logging
import time
from collections import deque

_LOG_BUFFER = deque(maxlen=500)  # in-memory logs for UI


class UILogHandler(logging.Handler):
    def emit(self, record):
        entry = {
            "ts": time.time(),
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        _LOG_BUFFER.append(entry)


logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s"
)

_root = logging.getLogger()
_root.addHandler(UILogHandler())


def get_logger(name: str):
    return logging.getLogger(name)


def get_logs():
    """Used by LogsPage"""
    return list(_LOG_BUFFER)


def clear_logs():
    _LOG_BUFFER.clear()
