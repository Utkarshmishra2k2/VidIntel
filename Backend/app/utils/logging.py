"""
Centralized logging. Import `logger` from here everywhere else in the app.
"""
import sys
import os
from loguru import logger
from config import config

logger.remove()

# Always log to stderr so it shows up when running locally / in containers
logger.add(sys.stderr, level=config.LOG_LEVEL)

# Also persist to a rotating file
os.makedirs("logs", exist_ok=True)
logger.add(
    "logs/app.log",
    level=config.LOG_LEVEL,
    rotation="10 MB",
    retention="1 week",
    enqueue=True,
)

__all__ = ["logger"]
