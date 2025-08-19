"""
Centralized credential management for Google APIs
Handles OAuth2 authentication and token refresh
"""

import json
import logging
from pathlib import Path
from typing import Optional, List
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import Flow

logger = logging.getLogger(__name__)

class CredentialManager:
    """
    Centralized credential management for Google APIs
    Handles loading, refreshing, and saving OAuth2 credentials
    """
    
    @staticmethod
    def get_google_credentials(
        credentials_path: Path, 
        scopes: List[str],
        token_file: Optional[Path] = None
    ) -> Optional[Credentials]:
        """
        Load and refresh Google credentials
        
        Args:
            credentials_path: Path to credentials JSON file
            scopes: List of required OAuth2 scopes
            token_file: Optional path to save token (defaults to credentials_path.with_suffix('.token'))
        
        Returns:
            Credentials object or None if authentication fails
        """
        if not credentials_path or not credentials_path.exists():
            logger.error(f"Credentials file not found: {credentials_path}")
            return None
        
        # Default token file location
        if token_file is None:
            token_file = credentials_path.with_suffix('.token')
        
        creds = None
        
        # Load existing token if available
        if token_file.exists():
            try:
                creds = Credentials.from_authorized_user_file(str(token_file), scopes)
                logger.info(f"Loaded existing token from {token_file}")
            except Exception as e:
                logger.warning(f"Failed to load token: {e}")
                creds = None
        
        # Check if credentials need refresh
        if creds and creds.expired and creds.refresh_token:
            try:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
                # Save refreshed credentials
                CredentialManager.save_credentials(creds, token_file)
                logger.info("Credentials refreshed successfully")
            except Exception as e:
                logger.error(f"Failed to refresh credentials: {e}")
                creds = None
        
        # If no valid credentials, need to authenticate
        if not creds or not creds.valid:
            logger.info("No valid credentials found, authentication required")
            creds = CredentialManager.authenticate_new(credentials_path, scopes, token_file)
        
        return creds
    
    @staticmethod
    def authenticate_new(
        credentials_path: Path,
        scopes: List[str],
        token_file: Path
    ) -> Optional[Credentials]:
        """
        Perform new OAuth2 authentication flow
        
        Args:
            credentials_path: Path to OAuth2 client credentials
            scopes: Required scopes
            token_file: Where to save the token
        
        Returns:
            New Credentials object or None
        """
        try:
            flow = Flow.from_client_secrets_file(
                str(credentials_path),
                scopes=scopes,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob'
            )
            
            # Get authorization URL
            auth_url, _ = flow.authorization_url(prompt='consent')
            
            print("\n" + "="*60)
            print("Google Authentication Required")
            print("="*60)
            print(f"\n1. Open this URL in your browser:\n{auth_url}")
            print("\n2. Grant permissions and copy the authorization code")
            
            # Get authorization code from user
            code = input("\n3. Paste the authorization code here: ").strip()
            
            # Exchange code for token
            flow.fetch_token(code=code)
            creds = flow.credentials
            
            # Save credentials
            CredentialManager.save_credentials(creds, token_file)
            logger.info(f"New credentials saved to {token_file}")
            
            return creds
            
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None
    
    @staticmethod
    def save_credentials(creds: Credentials, token_file: Path):
        """
        Save credentials to file
        
        Args:
            creds: Credentials to save
            token_file: Path to save token
        """
        try:
            token_data = {
                'token': creds.token,
                'refresh_token': creds.refresh_token,
                'token_uri': creds.token_uri,
                'client_id': creds.client_id,
                'client_secret': creds.client_secret,
                'scopes': creds.scopes
            }
            
            with open(token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            
            logger.info(f"Credentials saved to {token_file}")
            
        except Exception as e:
            logger.error(f"Failed to save credentials: {e}")
    
    @staticmethod
    def validate_credentials(creds: Credentials) -> bool:
        """
        Validate that credentials are valid and not expired
        
        Args:
            creds: Credentials to validate
        
        Returns:
            True if valid, False otherwise
        """
        if not creds:
            return False
        
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    return True
                except Exception:
                    return False
            return False
        
        return True
    
    @staticmethod
    def revoke_credentials(creds: Credentials) -> bool:
        """
        Revoke Google credentials
        
        Args:
            creds: Credentials to revoke
        
        Returns:
            True if revoked successfully
        """
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            import requests
            
            if creds and creds.token:
                response = requests.post(
                    'https://oauth2.googleapis.com/revoke',
                    params={'token': creds.token},
                    headers={'content-type': 'application/x-www-form-urlencoded'}
                )
                
                if response.status_code == 200:
                    logger.info("Credentials revoked successfully")
                    return True
                else:
                    logger.warning(f"Failed to revoke credentials: {response.status_code}")
                    return False
        except Exception as e:
            logger.error(f"Error revoking credentials: {e}")
            return False
        
        return False