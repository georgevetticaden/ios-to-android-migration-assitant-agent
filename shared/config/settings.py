"""
Centralized configuration for all MCP tools
Loads environment variables and provides validation
"""

import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

class Settings:
    """Centralized configuration for all migration tools"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for settings"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize settings from environment"""
        if not hasattr(self, 'initialized'):
            # Load .env file if it exists
            env_file = Path('.env')
            if env_file.exists():
                load_dotenv(env_file)
                logger.info(f"Loaded environment from {env_file}")
            else:
                logger.info("No .env file found, using system environment")
            
            # Database configuration
            self.MIGRATION_DB_PATH = Path(os.getenv(
                'MIGRATION_DB_PATH', 
                '~/.ios_android_migration/migration.db'
            )).expanduser()
            
            # Apple credentials
            self.APPLE_ID = os.getenv('APPLE_ID')
            self.APPLE_PASSWORD = os.getenv('APPLE_PASSWORD')
            
            # Google API credentials (paths to JSON files)
            google_photos_path = os.getenv('GOOGLE_PHOTOS_CREDENTIALS_PATH')
            self.GOOGLE_PHOTOS_CREDENTIALS_PATH = Path(google_photos_path).resolve() if google_photos_path else None
            
            gmail_path = os.getenv('GMAIL_CREDENTIALS_PATH')
            self.GMAIL_CREDENTIALS_PATH = Path(gmail_path).resolve() if gmail_path else None
            
            # Session management
            self.ICLOUD_SESSION_DIR = Path(os.getenv(
                'ICLOUD_SESSION_DIR',
                '~/.icloud_session'
            )).expanduser()
            
            # Logging configuration
            self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
            self.LOG_DIR = Path(os.getenv('LOG_DIR', './logs')).resolve()
            
            # API settings
            self.GOOGLE_PHOTOS_CACHE_TTL = int(os.getenv('GOOGLE_PHOTOS_CACHE_TTL', '3600'))
            self.GOOGLE_PHOTOS_RATE_LIMIT = int(os.getenv('GOOGLE_PHOTOS_RATE_LIMIT', '100'))
            self.PROGRESS_CHECK_INTERVAL_HOURS = int(os.getenv('PROGRESS_CHECK_INTERVAL_HOURS', '6'))
            
            # Screenshot directory
            self.SCREENSHOT_DIR = Path(os.getenv('SCREENSHOT_DIR', './screenshots')).resolve()
            
            # Browser settings
            self.BROWSER_HEADLESS = os.getenv('BROWSER_HEADLESS', 'false').lower() == 'true'
            self.BROWSER_TIMEOUT = int(os.getenv('BROWSER_TIMEOUT', '30000'))  # milliseconds
            
            # Create directories if they don't exist
            self.MIGRATION_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            self.ICLOUD_SESSION_DIR.mkdir(parents=True, exist_ok=True)
            self.LOG_DIR.mkdir(parents=True, exist_ok=True)
            self.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
            
            self.initialized = True
    
    def validate_required(self, tool_name: str = None) -> List[str]:
        """
        Validate required settings for a specific tool
        Returns list of error messages, empty if all valid
        """
        errors = []
        
        # Common validations
        if not self.MIGRATION_DB_PATH:
            errors.append("MIGRATION_DB_PATH not configured")
        
        # Tool-specific validations
        if tool_name == 'photo-migration':
            if not self.APPLE_ID:
                errors.append("APPLE_ID not configured")
            if not self.APPLE_PASSWORD:
                errors.append("APPLE_PASSWORD not configured")
            
            # Google Photos is optional but warn if not configured
            if not self.GOOGLE_PHOTOS_CREDENTIALS_PATH:
                logger.warning("GOOGLE_PHOTOS_CREDENTIALS_PATH not configured - progress tracking will be limited")
            elif not self.GOOGLE_PHOTOS_CREDENTIALS_PATH.exists():
                errors.append(f"Google Photos credentials file not found: {self.GOOGLE_PHOTOS_CREDENTIALS_PATH}")
            
            # Gmail is optional
            if self.GMAIL_CREDENTIALS_PATH and not self.GMAIL_CREDENTIALS_PATH.exists():
                logger.warning(f"Gmail credentials file not found: {self.GMAIL_CREDENTIALS_PATH}")
        
        elif tool_name == 'whatsapp':
            # Future WhatsApp-specific validations
            pass
        
        elif tool_name == 'family-services':
            # Future family services validations
            pass
        
        return errors
    
    def get_google_photos_scopes(self) -> List[str]:
        """Get required Google Photos API scopes"""
        return ['https://www.googleapis.com/auth/photoslibrary.readonly']
    
    def get_gmail_scopes(self) -> List[str]:
        """Get required Gmail API scopes"""
        return ['https://www.googleapis.com/auth/gmail.readonly']
    
    def to_dict(self) -> dict:
        """Export settings as dictionary (for debugging)"""
        return {
            'MIGRATION_DB_PATH': str(self.MIGRATION_DB_PATH),
            'APPLE_ID': self.APPLE_ID[:3] + '***' if self.APPLE_ID else None,
            'APPLE_PASSWORD': '***' if self.APPLE_PASSWORD else None,
            'GOOGLE_PHOTOS_CREDENTIALS_PATH': str(self.GOOGLE_PHOTOS_CREDENTIALS_PATH) if self.GOOGLE_PHOTOS_CREDENTIALS_PATH else None,
            'GMAIL_CREDENTIALS_PATH': str(self.GMAIL_CREDENTIALS_PATH) if self.GMAIL_CREDENTIALS_PATH else None,
            'ICLOUD_SESSION_DIR': str(self.ICLOUD_SESSION_DIR),
            'LOG_LEVEL': self.LOG_LEVEL,
            'LOG_DIR': str(self.LOG_DIR),
            'SCREENSHOT_DIR': str(self.SCREENSHOT_DIR),
            'BROWSER_HEADLESS': self.BROWSER_HEADLESS,
        }
    
    def __str__(self) -> str:
        """String representation for debugging"""
        return f"Settings(db={self.MIGRATION_DB_PATH.name}, apple_id={self.APPLE_ID[:3]}*** if configured)"

# Global settings getter
def get_settings() -> Settings:
    """Get the singleton settings instance"""
    return Settings()