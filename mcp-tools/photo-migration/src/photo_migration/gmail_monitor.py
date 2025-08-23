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
import webbrowser
import http.server
import socketserver
import threading
import urllib.parse

logger = logging.getLogger(__name__)

class GmailMonitor:
    """Gmail monitor for Apple transfer completion notifications.
    
    This class provides Gmail integration to automatically detect when
    Apple completes the iCloud to Google Photos transfer. It uses the
    Gmail API with OAuth2 authentication to search for and parse
    completion emails from Apple.
    
    **Key Features**:
        - Automatic browser-based OAuth flow on first use
        - Token persistence to avoid repeated authentication
        - Searches for Apple transfer completion emails
        - Extracts transfer details from email content
        - Broader scopes for future WhatsApp and family features
    
    **OAuth Scopes**:
        - gmail.readonly: Search and read emails
        - gmail.compose: Future feature - send notifications
        - gmail.modify: Future feature - manage labels
    
    **Used By**:
        - ICloudClient.check_completion_email() - Direct email check
        - ICloudClient.verify_transfer_complete() - Optional email verification
    
    **Email Detection**:
        Searches for emails from noreply@email.apple.com with subjects like:
        - "Your transfer request is complete"
        - "Your data transfer is ready"
        - "iCloud Photos transfer complete"
        - "Transfer to Google Photos complete"
    
    Attributes:
        credentials_path (Path): Path to OAuth2 credentials JSON file
        TOKEN_FILE (Path): Location of saved OAuth token
        creds: Google OAuth2 credentials object
        service: Gmail API service object
    """
    
    # Broader scopes for future WhatsApp and family services
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.compose',  # For sending emails
        'https://www.googleapis.com/auth/gmail.modify'    # For managing labels
    ]
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
                # Need new authorization - open browser automatically
                await self._browser_oauth_flow()
            
            # Save the token
            with open(self.TOKEN_FILE, 'wb') as token:
                pickle.dump(self.creds, token)
            logger.info(f"Saved Gmail token to {self.TOKEN_FILE}")
    
    async def _browser_oauth_flow(self):
        """Open browser for OAuth flow automatically"""
        logger.info("Starting browser-based Gmail OAuth flow...")
        
        # Use localhost redirect for automatic capture
        redirect_port = 8080
        redirect_uri = f'http://localhost:{redirect_port}'
        
        # Create OAuth flow
        flow = Flow.from_client_secrets_file(
            str(self.credentials_path),
            scopes=self.SCOPES,
            redirect_uri=redirect_uri
        )
        
        # Get authorization URL
        auth_url, _ = flow.authorization_url(
            prompt='consent',
            access_type='offline'
        )
        
        # Setup local server to capture the code
        auth_code_captured = threading.Event()
        captured_code = {'code': None}
        
        class OAuthHandler(http.server.SimpleHTTPRequestHandler):
            def do_GET(self):
                # Parse the URL to get the authorization code
                parsed_path = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed_path.query)
                
                if 'code' in params:
                    captured_code['code'] = params['code'][0]
                    # Send success response
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    success_html = """
                        <html>
                        <body style="font-family: Arial; padding: 50px; text-align: center;">
                            <h1 style="color: green;">Authorization Successful!</h1>
                            <p>You can close this window and return to the terminal.</p>
                            <script>window.setTimeout(function(){window.close();}, 3000);</script>
                        </body>
                        </html>
                    """
                    self.wfile.write(success_html.encode('utf-8'))
                    auth_code_captured.set()
                else:
                    # Send error response
                    self.send_response(400)
                    self.send_header('Content-type', 'text/html')
                    self.end_headers()
                    self.wfile.write(b"<h1>Error: No authorization code received</h1>")
            
            def log_message(self, format, *args):
                pass  # Suppress log messages
        
        # Start local server in a thread
        def run_server():
            with socketserver.TCPServer(("", redirect_port), OAuthHandler) as httpd:
                httpd.timeout = 120  # 2 minute timeout
                while not auth_code_captured.is_set():
                    httpd.handle_request()
        
        server_thread = threading.Thread(target=run_server, daemon=True)
        server_thread.start()
        
        print("\n" + "="*60)
        print("📧 Gmail Setup for Migration Monitoring")
        print("="*60)
        print("Opening your browser for one-time Gmail authorization...")
        print("This allows the migration agent to:")
        print("  • Monitor for Apple completion emails")
        print("  • Send WhatsApp bridge instructions (future)")
        print("  • Manage family service communications")
        print("\nPlease authorize in the browser window that opens.")
        print("="*60)
        
        # Open browser
        webbrowser.open(auth_url)
        logger.info(f"Opened browser with OAuth URL")
        
        # Wait for authorization code
        if auth_code_captured.wait(timeout=120):
            if captured_code['code']:
                # Exchange code for token
                flow.fetch_token(code=captured_code['code'])
                self.creds = flow.credentials
                logger.info("Successfully obtained Gmail authorization!")
                print("\n✅ Gmail authorization complete!")
            else:
                raise Exception("No authorization code captured")
        else:
            raise Exception("Authorization timeout - no response received")
        
        logger.info("Gmail OAuth flow completed")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def check_for_completion_email(self, 
                                        transfer_id: str = None,
                                        since_hours: int = 72) -> Dict[str, Any]:
        """Check Gmail for Apple transfer completion notification.
        
        Searches the user's Gmail inbox for emails from Apple confirming
        that the photo transfer to Google Photos has completed. This is
        the primary method called by the MCP tool.
        
        **Search Strategy**:
        1. Filters emails from Apple's noreply address
        2. Searches for known completion subject patterns
        3. Optionally searches for specific transfer ID in body
        4. Returns most recent matching email
        
        **Email Processing**:
        - Extracts subject, sender, and date
        - Parses body for photo/video counts
        - Identifies destination service confirmation
        - Provides summary of key information
        
        Args:
            transfer_id: Optional transfer ID to search for in email body.
                        If provided, narrows search to emails mentioning this ID.
            since_hours: How many hours back to search. Defaults to 72 (3 days).
                        Increase for older transfers.
        
        Returns:
            Dict containing:
                - found: Boolean indicating if completion email was found
                - email_id: Gmail message ID (if found)
                - received_at: Timestamp when email was received
                - subject: Email subject line
                - transfer_complete: Boolean confirming transfer status
                - details: Extracted information from email body
                - checked_at: Current timestamp
                - search_window_hours: Hours searched
        
        Example Response (Found):
            {
                "found": true,
                "email_id": "18b5f3d2a9c7e4f1",
                "received_at": "Mon, 24 Aug 2025 16:30:00 -0700",
                "subject": "Your transfer to Google Photos is complete",
                "transfer_complete": true,
                "details": {
                    "status": "complete",
                    "photos_mentioned": "60,238",
                    "videos_mentioned": "2,418",
                    "destination_confirmed": "Google Photos",
                    "summary": "Your transfer of 60,238 photos and 2,418 videos..."
                },
                "checked_at": "2025-08-22T10:00:00Z"
            }
        
        Example Response (Not Found):
            {
                "found": false,
                "checked_at": "2025-08-22T10:00:00Z",
                "search_window_hours": 72
            }
        
        Raises:
            HttpError: If Gmail API request fails
            Exception: If email parsing encounters errors
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
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return []
        except Exception as e:
            logger.error(f"Failed to search emails: {e}")
            return []
    
    async def authenticate(self):
        """Authenticate with Gmail API (alias for initialize)"""
        await self.initialize()
    
    async def search_emails(self, query: str, after_date: str = None, limit: int = 10) -> List[Dict]:
        """Search emails with given query
        
        Args:
            query: Gmail search query
            after_date: Optional date filter (YYYY/MM/DD format)
            limit: Maximum number of results
            
        Returns:
            List of email dictionaries
        """
        try:
            if not self.service:
                await self.initialize()
            
            # Build query
            if after_date:
                query = f"{query} after:{after_date}"
            
            logger.info(f"Searching emails with query: {query}")
            
            # Search messages
            results = self.service.users().messages().list(
                userId='me',
                q=query,
                maxResults=limit
            ).execute()
            
            messages = results.get('messages', [])
            email_list = []
            
            for msg in messages:
                try:
                    message = self.service.users().messages().get(
                        userId='me',
                        id=msg['id']
                    ).execute()
                    
                    email_data = await self._parse_email(message)
                    if email_data:
                        email_list.append(email_data)
                except Exception as e:
                    logger.warning(f"Failed to fetch message {msg['id']}: {e}")
                    continue
            
            logger.info(f"Found {len(email_list)} emails")
            return email_list
            
        except Exception as e:
            logger.error(f"Failed to get recent emails: {e}")
            return []
    
    async def _parse_email(self, message):
        """Parse email message to extract relevant data"""
        try:
            headers = message['payload'].get('headers', [])
            
            # Extract header fields
            subject = ''
            from_addr = ''
            date = ''
            
            for header in headers:
                name = header['name'].lower()
                if name == 'subject':
                    subject = header['value']
                elif name == 'from':
                    from_addr = header['value']
                elif name == 'date':
                    date = header['value']
            
            # Extract body
            body = ''
            if 'parts' in message['payload']:
                for part in message['payload']['parts']:
                    if part['mimeType'] == 'text/plain':
                        data = part['body'].get('data', '')
                        if data:
                            import base64
                            body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                        break
            elif message['payload']['body'].get('data'):
                import base64
                body = base64.urlsafe_b64decode(
                    message['payload']['body']['data']
                ).decode('utf-8', errors='ignore')
            
            return {
                'id': message['id'],
                'subject': subject,
                'from': from_addr,
                'date': date,
                'body': body[:500]  # Limit body length
            }
        except Exception as e:
            logger.warning(f"Failed to parse email: {e}")
            return None
    
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