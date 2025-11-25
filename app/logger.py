"""
Logging Configuration - Centralized logging setup for the RDFM Artifact GUI

This module provides a simple logging configuration that logs to both file and console.
"""

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    log_file: Optional[str] = None,
    console_level: int = logging.INFO,
    file_level: int = logging.DEBUG
) -> logging.Logger:
    """Setup application logging with both file and console handlers

    Args:
        log_file: Path to log file. If None, logs to ~/.rdfm-artifact-gui/app.log
        console_level: Logging level for console output (default: INFO)
        file_level: Logging level for file output (default: DEBUG)

    Returns:
        Configured logger instance
    """
    # Get the root logger for the app
    logger = logging.getLogger('rdfm_artifact_gui')
    logger.setLevel(logging.DEBUG)  # Capture all levels, handlers will filter

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(console_level)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # Rotating file handler (5 files, 1MB each)
    if log_file is None:
        log_dir = Path.home() / '.rdfm-artifact-gui'
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = str(log_dir / 'app.log')

    try:
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(file_level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        logger.info(f"Logging to file: {log_file} (rotating, max 5 files @ 1MB each)")
    except (OSError, PermissionError) as e:
        logger.warning(f"Could not create log file {log_file}: {e}")

    # Prevent propagation to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module

    Args:
        name: Name of the module (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f'rdfm_artifact_gui.{name}')
