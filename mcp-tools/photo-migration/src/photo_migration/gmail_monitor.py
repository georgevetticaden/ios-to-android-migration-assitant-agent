"""
Gmail API client for monitoring Apple transfer completion emails
Searches for and parses transfer status notifications
"""

import os
import re
import logging
import pickle
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from base64 import urlsafe_b64decode

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class GmailMonitor:
    """Monitor Gmail for Apple transfer completion emails"""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    TOKEN_FILE = Path.home() / '.ios_android_migration' / 'gmail_token.pickle'
    
    # Email patterns to search for
    APPLE_SENDER = "noreply@email.apple.com"
    TRANSFER_SUBJECTS = [
        "Your transfer request is complete",
        "Your data transfer is ready",
        "iCloud Photos transfer complete",
        "Transfer to Google Photos complete"
    ]
    
    def __init__(self, credentials_path: str = None):
        """Initialize Gmail monitor
        
        Args:
            credentials_path: Path to OAuth2 credentials JSON file
        """
        self.credentials_path = credentials_path or os.getenv('GMAIL_CREDENTIALS_PATH')
        if not self.credentials_path:
            raise ValueError("GMAIL_CREDENTIALS_PATH not configured")
        
        self.credentials_path = Path(self.credentials_path).expanduser().resolve()
        if not self.credentials_path.exists():
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_path}")
        
        self.creds = None
        self.service = None
        
        # Ensure token directory exists
        self.TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"GmailMonitor initialized with credentials from {self.credentials_path}")
    
    async def initialize(self):
        """Initialize the Gmail service"""
        await self._authenticate()
        self.service = build('gmail', 'v1', credentials=self.creds)
        logger.info("Gmail service initialized")
    
    async def _authenticate(self):
        """Handle OAuth2 authentication flow"""
        # Try to load existing token
        if self.TOKEN_FILE.exists():
            try:
                with open(self.TOKEN_FILE, 'rb') as token:
                    self.creds = pickle.load(token)
                logger.info("Loaded existing Gmail token")
            except Exception as e:
                logger.warning(f"Could not load token: {e}")
                self.creds = None
        
        # Refresh or get new token
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                    logger.info("Refreshed Gmail token")
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}")
                    self.creds = None
            
            if not self.creds:
                # Need new authorization
                flow = Flow.from_client_secrets_file(
                    str(self.credentials_path),
                    scopes=self.SCOPES,
                    redirect_uri='urn:ietf:wg:oauth:2.0:oob'
                )
                
                # Get authorization URL
                auth_url, _ = flow.authorization_url(
                    prompt='consent',
                    access_type='offline'
                )
                
                print("\n" + "="*60)
                print("Gmail Authorization Required")
                print("="*60)
                print(f"\n1. Visit this URL:\n{auth_url}\n")
                print("2. Sign in and authorize the application")
                print("3. Copy the authorization code")
                auth_code = input("\nEnter the authorization code: ").strip()
                
                # Exchange code for token
                flow.fetch_token(code=auth_code)
                self.creds = flow.credentials
                
                logger.info("Obtained new Gmail authorization")
            
            # Save the token
            with open(self.TOKEN_FILE, 'wb') as token:
                pickle.dump(self.creds, token)
            logger.info(f"Saved Gmail token to {self.TOKEN_FILE}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def check_for_completion_email(self, 
                                        transfer_id: str = None,
                                        since_hours: int = 72) -> Dict[str, Any]:
        """Check for Apple transfer completion email
        
        Args:
            transfer_id: Optional transfer ID to search for
            since_hours: How many hours back to search (default 72)
        
        Returns:
            Dictionary with email details if found
        """
        try:
            # Build search query
            query_parts = [f"from:{self.APPLE_SENDER}"]
            
            # Add subject search
            subject_query = " OR ".join([f'subject:"{subj}"' for subj in self.TRANSFER_SUBJECTS])
            query_parts.append(f"({subject_query})")
            
            # Add date filter
            since_date = (datetime.now() - timedelta(hours=since_hours)).strftime("%Y/%m/%d")
            query_parts.append(f"after:{since_date}")
            
            # Add transfer ID if provided
            if transfer_id:
                query_parts.append(f'"{transfer_id}"')
            
            query = " ".join(query_parts)
            logger.info(f"Searching Gmail with query: {query}")
            
            # Search for messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=10
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                logger.info("No completion emails found")
                return {
                    "found": False,
                    "checked_at": datetime.now().isoformat(),
                    "search_window_hours": since_hours
                }
            
            # Get the most recent message
            latest_msg_id = messages[0]['id']
            message = self.service.users().messages().get(
                userId='me',
                id=latest_msg_id
            ).execute()
            
            # Parse email details
            email_data = await self._parse_completion_email(message)
            
            return {
                "found": True,
                "email_id": latest_msg_id,
                "received_at": email_data.get("date"),
                "subject": email_data.get("subject"),
                "transfer_complete": True,
                "details": email_data.get("body_extract"),
                "checked_at": datetime.now().isoformat()
            }
            
        except HttpError as e:
            logger.error(f"Gmail API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to check completion email: {e}")
            raise
    
    async def _parse_completion_email(self, message: Dict) -> Dict[str, Any]:
        """Parse Apple completion email for details
        
        Args:
            message: Gmail message object
        
        Returns:
            Parsed email data
        """
        try:
            headers = message['payload'].get('headers', [])
            
            # Extract headers
            email_data = {}
            for header in headers:
                name = header['name'].lower()
                if name == 'subject':
                    email_data['subject'] = header['value']
                elif name == 'from':
                    email_data['from'] = header['value']
                elif name == 'date':
                    email_data['date'] = header['value']
            
            # Extract body
            body_text = await self._get_message_body(message)
            if body_text:
                # Try to extract key information from body
                email_data['body_extract'] = self._extract_transfer_info(body_text)
            
            logger.info(f"Parsed email: {email_data.get('subject', 'No subject')}")
            return email_data
            
        except Exception as e:
            logger.error(f"Failed to parse email: {e}")
            return {}
    
    async def _get_message_body(self, message: Dict) -> str:
        """Extract body text from Gmail message
        
        Args:
            message: Gmail message object
        
        Returns:
            Message body text
        """
        try:
            payload = message['payload']
            body = ""
            
            # Check for parts (multipart message)
            if 'parts' in payload:
                for part in payload['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body']['data']
                        body = urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
                    elif part['mimeType'] == 'text/html' and not body:
                        # Fallback to HTML if no plain text
                        data = part['body']['data']
                        html = urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        # Basic HTML stripping
                        body = re.sub('<[^<]+?>', '', html)
            else:
                # Simple message
                if payload['body'].get('data'):
                    body = urlsafe_b64decode(
                        payload['body']['data']
                    ).decode('utf-8', errors='ignore')
            
            return body.strip()
            
        except Exception as e:
            logger.error(f"Failed to extract message body: {e}")
            return ""
    
    def _extract_transfer_info(self, body: str) -> Dict[str, str]:
        """Extract transfer information from email body
        
        Args:
            body: Email body text
        
        Returns:
            Extracted information
        """
        info = {}
        
        # Look for completion confirmation
        if "complete" in body.lower() or "ready" in body.lower():
            info["status"] = "complete"
        
        # Try to extract photo/video counts
        photo_match = re.search(r'(\d+(?:,\d+)*)\s*photos?', body, re.IGNORECASE)
        if photo_match:
            info["photos_mentioned"] = photo_match.group(1)
        
        video_match = re.search(r'(\d+(?:,\d+)*)\s*videos?', body, re.IGNORECASE)
        if video_match:
            info["videos_mentioned"] = video_match.group(1)
        
        # Look for Google Photos mention
        if "google photos" in body.lower():
            info["destination_confirmed"] = "Google Photos"
        
        # Extract first 200 chars as summary
        info["summary"] = body[:200].replace('\n', ' ').strip()
        
        return info
    
    async def get_recent_apple_emails(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get recent emails from Apple for debugging
        
        Args:
            limit: Maximum number of emails to return
        
        Returns:
            List of email summaries
        """
        try:
            query = f"from:{self.APPLE_SENDER}"
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            email_list = []
            
            for msg in messages:
                message = self.service.users().messages().get(
                    userId='me',
                    id=msg['id']
                ).execute()
                
                headers = message['payload'].get('headers', [])
                subject = None
                date = None
                
                for header in headers:
                    if header['name'] == 'Subject':
                        subject = header['value']
                    elif header['name'] == 'Date':
                        date = header['value']
                
                email_list.append({
                    "id": msg['id'],
                    "subject": subject,
                    "date": date
                })
            
            return email_list
            
        except Exception as e:
            logger.error(f"Failed to get recent emails: {e}")
            return []
    
    async def cleanup(self):
        """Cleanup resources"""
        if self.service:
            # Close service connection if needed
            pass
        logger.info("Gmail monitor cleaned up")

# Convenience function for standalone testing
async def test_gmail_monitor():
    """Test Gmail monitor functionality"""
    try:
        monitor = GmailMonitor()
        await monitor.initialize()
        
        print("\n=== Testing Gmail Monitor ===")
        
        # Test checking for completion email
        print("\n1. Checking for transfer completion email...")
        result = await monitor.check_for_completion_email(since_hours=168)  # Last week
        
        if result['found']:
            print(f"   ✅ Found completion email!")
            print(f"   Subject: {result.get('subject')}")
            print(f"   Received: {result.get('received_at')}")
            if result.get('details'):
                print(f"   Details: {result['details']}")
        else:
            print(f"   No completion email found in last 168 hours")
        
        # Test getting recent Apple emails
        print("\n2. Getting recent Apple emails...")
        emails = await monitor.get_recent_apple_emails(limit=3)
        for email in emails:
            print(f"   - {email['subject']} ({email['date']})")
        
        await monitor.cleanup()
        print("\n✅ Gmail monitor test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # For testing
    import asyncio
    asyncio.run(test_gmail_monitor())