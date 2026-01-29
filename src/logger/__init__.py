from .base import BaseLogger
from .decorator import log_function

get_logger = BaseLogger.get_logger

__all__ = ["BaseLogger", "log_function", "get_logger"]
