"""
Centralized logging configuration for migration-state MCP server.
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
    # From: mcp-tools/migration-state/logging_config.py
    # To: ios-to-android-migration-assitant-agent/logs
    # Path structure: .../ios-to-android-migration-assitant-agent/mcp-tools/migration-state/
    # Need to go up 3 levels: migration-state -> mcp-tools -> ios-to-android-migration-assitant-agent
    project_root = Path(__file__).parent.parent.parent
    log_dir = project_root / "logs"
    
    # Create logs directory if it doesn't exist
    log_dir.mkdir(exist_ok=True)
    
    # Create log file with date
    log_file = log_dir / f"migration_state_{datetime.now().strftime('%Y%m%d')}.log"
    
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
    
    # Console handler - less verbose for production
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def get_test_logger(name: str = "test", verbose: bool = False):
    """
    Get a logger configured for testing with colored output.
    
    Args:
        name: Logger name for the test
        verbose: If True, show DEBUG level logs
    
    Returns:
        Configured logger for testing
    """
    # For tests, we want more colorful console output
    project_root = Path(__file__).parent.parent.parent
    log_dir = project_root / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Test log file
    log_file = log_dir / f"test_migration_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Configure test logger
    logger = logging.getLogger(f"test.{name}")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers = []
    
    # File handler - all details
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Console handler with custom formatter for tests
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    
    # Custom formatter with colors
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            'DEBUG': '\033[36m',    # Cyan
            'INFO': '\033[32m',     # Green
            'WARNING': '\033[33m',  # Yellow
            'ERROR': '\033[31m',    # Red
            'CRITICAL': '\033[35m', # Magenta
        }
        RESET = '\033[0m'
        BOLD = '\033[1m'
        
        def format(self, record):
            # Add color to level name
            levelname = record.levelname
            if levelname in self.COLORS:
                record.levelname = f"{self.COLORS[levelname]}{self.BOLD}{levelname}{self.RESET}"
            
            # Format the message
            if levelname == 'INFO' and record.msg.startswith('✅'):
                # Success messages
                record.msg = f"\033[32m{record.msg}\033[0m"
            elif levelname == 'ERROR' or record.msg.startswith('❌'):
                # Error messages
                record.msg = f"\033[31m{record.msg}\033[0m"
            elif record.msg.startswith('⚠️'):
                # Warning messages
                record.msg = f"\033[33m{record.msg}\033[0m"
            
            return super().format(record)
    
    console_formatter = ColoredFormatter('%(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger