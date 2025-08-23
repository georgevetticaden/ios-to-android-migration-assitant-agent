"""
Centralized logging configuration for photo migration tools.
All logs go to the main project logs directory.
"""

import logging
import os
from pathlib import Path
from datetime import datetime

def setup_logging(name: str = None, level=logging.INFO):
    """
    Set up logging configuration that writes to the main project logs directory.
    
    Args:
        name: Logger name (defaults to root logger)
        level: Logging level (default INFO)
    
    Returns:
        Configured logger instance
    """
    # Main project logs directory
    # From: mcp-tools/photo-migration/src/photo_migration/logging_config.py
    # To: ios-to-android-migration-assitant-agent/logs
    # Path structure: .../ios-to-android-migration-assitant-agent/mcp-tools/photo-migration/src/photo_migration/
    # Need to go up 5 levels: photo_migration -> src -> photo-migration -> mcp-tools -> ios-to-android-migration-assitant-agent
    project_root = Path(__file__).parent.parent.parent.parent.parent
    log_dir = project_root / "logs"
    
    # Create logs directory if it doesn't exist
    log_dir.mkdir(exist_ok=True)
    
    # Create log file with date
    log_file = log_dir / f"photo_migration_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Configure logger
    logger = logging.getLogger(name) if name else logging.getLogger()
    logger.setLevel(level)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers = []
    
    # File handler - detailed logs
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler - less verbose
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_screenshot_dir():
    """Get the main project logs directory for screenshots."""
    # Same path as logging - ios-to-android-migration-assitant-agent/logs
    # Need to go up 5 levels to reach project root
    project_root = Path(__file__).parent.parent.parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    return log_dir