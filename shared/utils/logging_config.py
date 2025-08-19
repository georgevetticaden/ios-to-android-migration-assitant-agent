"""
Centralized logging configuration for all MCP tools
Provides consistent logging setup across the migration system
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

def setup_logging(
    name: str = None,
    level: str = None,
    log_dir: Path = None,
    console: bool = True,
    file: bool = True
) -> logging.Logger:
    """
    Set up logging configuration for a tool
    
    Args:
        name: Logger name (defaults to root logger)
        level: Log level (defaults to INFO)
        log_dir: Directory for log files (defaults to ./logs)
        console: Enable console output
        file: Enable file output
    
    Returns:
        Configured logger instance
    """
    # Get settings for defaults
    from shared.config.settings import get_settings
    settings = get_settings()
    
    # Use provided values or defaults from settings
    log_level = level or settings.LOG_LEVEL
    log_directory = log_dir or settings.LOG_DIR
    
    # Ensure log directory exists
    log_directory.mkdir(parents=True, exist_ok=True)
    
    # Get or create logger
    logger = logging.getLogger(name) if name else logging.getLogger()
    logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear any existing handlers
    logger.handlers.clear()
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        console_handler.setFormatter(simple_formatter)
        logger.addHandler(console_handler)
    
    # File handler
    if file and name:
        # Create tool-specific log file
        timestamp = datetime.now().strftime('%Y%m%d')
        log_file = log_directory / f"{name}_{timestamp}.log"
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)
        
        # Also create a latest symlink for easy access
        latest_link = log_directory / f"{name}_latest.log"
        if latest_link.exists() or latest_link.is_symlink():
            latest_link.unlink()
        latest_link.symlink_to(log_file.name)
    
    # Log initialization
    logger.info(f"Logging initialized for {name or 'root'} at level {log_level}")
    if file and name:
        logger.info(f"Log file: {log_file}")
    
    return logger

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with default configuration
    
    Args:
        name: Logger name
    
    Returns:
        Configured logger
    """
    return setup_logging(name=name)

class MigrationLogAdapter(logging.LoggerAdapter):
    """
    Custom log adapter that adds migration context to all log messages
    """
    
    def __init__(self, logger: logging.Logger, migration_id: str):
        """
        Initialize adapter with migration context
        
        Args:
            logger: Base logger
            migration_id: Current migration ID
        """
        super().__init__(logger, {'migration_id': migration_id})
    
    def process(self, msg, kwargs):
        """Add migration ID to all log messages"""
        return f"[{self.extra['migration_id']}] {msg}", kwargs

def get_migration_logger(name: str, migration_id: str) -> MigrationLogAdapter:
    """
    Get a logger with migration context
    
    Args:
        name: Logger name
        migration_id: Migration ID to include in logs
    
    Returns:
        Logger adapter with migration context
    """
    base_logger = setup_logging(name=name)
    return MigrationLogAdapter(base_logger, migration_id)

# Utility functions for common logging patterns

def log_api_call(logger: logging.Logger, service: str, method: str, **kwargs):
    """Log API call details"""
    logger.debug(f"API Call: {service}.{method} with params: {kwargs}")

def log_error_with_context(logger: logging.Logger, error: Exception, context: dict):
    """Log error with additional context"""
    logger.error(f"Error: {str(error)}", extra={'context': context}, exc_info=True)

def log_progress(logger: logging.Logger, current: int, total: int, task: str):
    """Log progress of a task"""
    percentage = (current / total * 100) if total > 0 else 0
    logger.info(f"Progress: {task} - {current}/{total} ({percentage:.1f}%)")

def log_timing(logger: logging.Logger, operation: str, duration_seconds: float):
    """Log operation timing"""
    logger.info(f"Timing: {operation} completed in {duration_seconds:.2f} seconds")