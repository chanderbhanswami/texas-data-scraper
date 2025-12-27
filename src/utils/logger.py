"""
Logging utilities for Texas Data Scraper
"""
import sys
from pathlib import Path
from loguru import logger
from config.settings import LOG_DIR, log_config

# Remove default handler
logger.remove()

# Add console handler with color
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=log_config.LEVEL,
    colorize=True
)

# Add file handler with rotation
logger.add(
    LOG_DIR / "texas_scraper_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation=log_config.MAX_SIZE,
    retention=log_config.BACKUP_COUNT,
    compression="zip"
)

# Add error-specific log file
logger.add(
    LOG_DIR / "errors_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation=log_config.MAX_SIZE,
    retention=log_config.BACKUP_COUNT,
    compression="zip"
)


def get_logger(name: str):
    """Get a logger instance with the specified name"""
    return logger.bind(name=name)