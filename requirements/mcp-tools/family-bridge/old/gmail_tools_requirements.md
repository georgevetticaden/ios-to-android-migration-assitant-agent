# Gmail Tools Module - Complete Requirements Document
## Universal Email Orchestration for Family Bridge Services

### Project Context
This document specifies requirements for a Gmail tools module that the AI agent uses to orchestrate email communications across all family bridge services (WhatsApp, Venmo Teen, Life360). The agent calls this module directly to send personalized family setup emails, rather than having individual services handle their own email sending. This centralized approach ensures consistent messaging and allows the agent to maintain full control over family communication orchestration.

**CRITICAL**: Gmail uses OAuth 2.0 authentication. Credentials are retrieved from environment variables pointing to OAuth credential files, NOT passwords.

---

## 1. Project Structure & Integration

### 1.1 MCP Tool Architecture
```
mcp-tools/
├── gmail-tools/
│   ├── src/gmail_tools/
│   │   ├── __init__.py
│   │   ├── gmail_client.py           # Main Gmail API client
│   │   ├── oauth_manager.py          # OAuth token management
│   │   ├── email_templates.py        # Service-specific templates
│   │   ├── family_manager.py         # Family member tracking
│   │   ├── server.py                 # MCP server implementation
│   │   └── email_validator.py        # Email validation utilities
│   ├── test_gmail.py                 # Standalone testing
│   ├── setup_oauth.py                # OAuth credential setup helper
│   ├── pyproject.toml
│   ├── .env
│   └── README.md
```

### 1.2 Integration Points
- **Database**: Shares DuckDB with photo-migration for tracking email sends
- **OAuth Pattern**: Uses Google OAuth 2.0 with credential files
- **MCP Server**: Independent server that agent calls directly
- **Service Agnostic**: Works for any family bridge service

---

## 2. Gmail OAuth Authentication

### 2.1 OAuth Setup Requirements

```python
class GmailOAuthManager:
    """Manages Gmail OAuth authentication and token refresh"""
    
    def __init__(self):
        # Get credential path from environment
        self.creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
        if not self.creds_path:
            raise ValueError("GMAIL_CREDENTIALS_PATH not configured in environment")
        
        self.token_file = Path.home() / ".gmail_token" / "token.json"
        self.token_file.parent.mkdir(exist_ok=True)
        
        # OAuth scopes needed
        self.SCOPES = [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/gmail.modify'
        ]
    
    async def authenticate(self) -> Credentials:
        """Get valid Gmail credentials, refreshing if necessary"""
        creds = None
        
        # Load existing token
        if self.token_file.exists():
            creds = Credentials.from_authorized_user_file(
                str(self.token_file), 
                self.SCOPES
            )
        
        # If no valid credentials, need to authenticate
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                # Refresh the token
                creds.refresh(Request())
            else:
                # Need new authentication
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.creds_path, 
                    self.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            self.token_file.write_text(creds.to_json())
        
        return creds
```

### 2.2 One-Time OAuth Setup Helper

```python
# setup_oauth.py - Run once to set up Gmail OAuth
import os
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

def setup_gmail_oauth():
    """One-time setup for Gmail OAuth credentials"""
    
    print("=" * 60)
    print("Gmail OAuth Setup")
    print("=" * 60)
    print("\nBefore running this:")
    print("1. Go to Google Cloud Console")
    print("2. Create OAuth 2.0 credentials")
    print("3. Download the credentials JSON")
    print("4. Set GMAIL_CREDENTIALS_PATH to point to the JSON file")
    print("=" * 60)
    
    creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
    if not creds_path or not os.path.exists(creds_path):
        print("ERROR: GMAIL_CREDENTIALS_PATH not set or file doesn't exist")
        return
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.send']
    
    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Save the credentials
    token_path = os.path.expanduser("~/.gmail_token/token.json")
    os.makedirs(os.path.dirname(token_path), exist_ok=True)
    
    with open(token_path, 'w') as token:
        token.write(creds.to_json())
    
    print(f"\n✅ OAuth setup complete! Token saved to {token_path}")
    print("You can now use the Gmail tools module")

if __name__ == "__main__":
    setup_gmail_oauth()
```

---

## 3. Main Gmail Client Implementation

### 3.1 Core Gmail Client

```python
import os
import base64
import logging
from typing import Dict, Any, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class GmailClient:
    """Main Gmail client for sending family bridge emails"""
    
    def __init__(self):
        self.oauth_manager = GmailOAuthManager()
        self.service = None
        self.user_email = None
    
    async def initialize(self):
        """Initialize Gmail service"""
        try:
            creds = await self.oauth_manager.authenticate()
            self.service = build('gmail', 'v1', credentials=creds)
            
            # Get user's email address
            profile = self.service.users().getProfile(userId='me').execute()
            self.user_email = profile['emailAddress']
            logger.info(f"Gmail client initialized for {self.user_email}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Gmail client: {e}")
            raise
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        body_html: str,
        body_text: Optional[str] = None,
        cc_emails: Optional[List[str]] = None,
        from_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send an email via Gmail API
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body_html: HTML body content
            body_text: Plain text body (optional)
            cc_emails: List of CC recipients
            from_name: Display name for sender
        
        Returns:
            Dict with status and message ID
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['To'] = to_email
            message['Subject'] = subject
            
            # Set From with display name if provided
            if from_name:
                message['From'] = f"{from_name} <{self.user_email}>"
            else:
                message['From'] = self.user_email
            
            # Add CC if provided
            if cc_emails:
                message['Cc'] = ', '.join(cc_emails)
            
            # Add text and HTML parts
            if body_text:
                text_part = MIMEText(body_text, 'plain')
                message.attach(text_part)
            
            html_part = MIMEText(body_html, 'html')
            message.attach(html_part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')
            
            # Send message
            send_message = {'raw': raw_message}
            result = self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()
            
            # Log to database
            await self._log_email_sent(
                to_email=to_email,
                subject=subject,
                service_type="unknown",
                message_id=result['id']
            )
            
            logger.info(f"Email sent to {to_email}: {result['id']}")
            
            return {
                "status": "sent",
                "message_id": result['id'],
                "to": to_email,
                "subject": subject
            }
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return {
                "status": "error",
                "message": f"Failed to send email: {str(error)}",
                "to": to_email
            }
        except Exception as e:
            logger.error(f"Email send error: {e}")
            return {
                "status": "error",
                "message": f"Failed to send email: {str(e)}",
                "to": to_email
            }
    
    async def _log_email_sent(
        self, 
        to_email: str, 
        subject: str, 
        service_type: str,
        message_id: str
    ):
        """Log email send to database"""
        try:
            import duckdb
            from datetime import datetime
            
            db_path = os.getenv('DUCKDB_PATH', './data/photo_migration.db')
            conn = duckdb.connect(db_path)
            
            conn.execute("""
                INSERT INTO email_logs 
                (to_email, subject, service_type, message_id, sent_at, status)
                VALUES (?, ?, ?, ?, ?, 'sent')
            """, [to_email, subject, service_type, message_id, datetime.now()])
            
            conn.close()
            
        except Exception as e:
            logger.error(f"Failed to log email: {e}")
```

---

## 4. Email Templates for Each Service

### 4.1 Service-Specific Email Templates

```python
class EmailTemplates:
    """Email templates for each family bridge service"""
    
    @staticmethod
    def whatsapp_invite(
        recipient_name: str,
        group_name: str,
        invite_link: str,
        relationship: str = "family member"
    ) -> Dict[str, str]:
        """Generate WhatsApp invite email"""
        
        # Personalize based on relationship
        if relationship == "spouse":
            greeting = f"Hi {recipient_name},"
            tone = "I know you love iMessage, but this will make it easier for us to stay connected now that I'm on Android."
        elif relationship == "child":
            greeting = f"Hey {recipient_name}!"
            tone = "This is way better than iMessage - you can send bigger videos and it works on any phone!"
        else:
            greeting = f"Hi {recipient_name},"
            tone = "This will help us stay connected across iPhone and Android."
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #25D366;">Join Our Family WhatsApp Group! 📱</h2>
            
            <p>{greeting}</p>
            
            <p>{tone}</p>
            
            <div style="background: #f0f0f0; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3>Group: {group_name}</h3>
                <p><strong>Click to join:</strong></p>
                <a href="{invite_link}" style="display: inline-block; background: #25D366; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Join WhatsApp Group
                </a>
            </div>
            
            <h3>Why WhatsApp is Better Than iMessage:</h3>
            <ul>
                <li>✅ Works on ANY phone (iPhone, Android, even tablets!)</li>
                <li>✅ Better photo and video quality</li>
                <li>✅ Larger file sizes (up to 2GB!)</li>
                <li>✅ Read receipts and typing indicators</li>
                <li>✅ Free international messaging</li>
                <li>✅ You keep your iPhone - nothing changes!</li>
            </ul>
            
            <h3>Simple Setup (2 minutes):</h3>
            <ol>
                <li>Download WhatsApp from the App Store</li>
                <li>Sign up with your phone number</li>
                <li>Click the invite link above</li>
                <li>You're in the family group!</li>
            </ol>
            
            <p style="color: #666; font-size: 14px;">
                Don't worry - you're not switching from iPhone! This just gives us a better way to chat as a family.
            </p>
            
            <p>Love,<br>Dad 📱➡️🤖</p>
        </body>
        </html>
        """
        
        text_body = f"""
{greeting}

{tone}

Join our family WhatsApp group: {group_name}

Click here: {invite_link}

Why WhatsApp is better than iMessage:
- Works on ANY phone
- Better photo/video quality
- Larger file sizes
- Free international messaging
- You keep your iPhone!

Simple setup:
1. Download WhatsApp
2. Sign up with your number
3. Click the invite link
4. You're in!

Love,
Dad
        """
        
        return {
            "html": html_body,
            "text": text_body
        }
    
    @staticmethod
    def venmo_teen_instructions(
        teen_name: str,
        signup_link: str,
        allowance_amount: str,
        allowance_reason: str,
        teen_age: int
    ) -> Dict[str, str]:
        """Generate Venmo Teen setup instructions"""
        
        # Age-appropriate messaging
        if teen_age >= 16:
            excitement = "This is what everyone at school uses!"
            benefits = "Split costs with friends, get your allowance instantly, and learn money management."
        else:
            excitement = "Your friends probably already use this!"
            benefits = "Get your allowance digitally and learn to manage money like a pro."
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #3D95CE;">Your Venmo Teen Account is Ready! 💰</h2>
            
            <p>Hey {teen_name}!</p>
            
            <p>Great news - I've set up a Venmo Teen account for you! {excitement}</p>
            
            <div style="background: #f8f8f8; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3>Your Allowance Details:</h3>
                <p style="font-size: 24px; color: #3D95CE; margin: 10px 0;">
                    <strong>{allowance_amount}</strong> for {allowance_reason}
                </p>
            </div>
            
            <div style="background: #3D95CE; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="color: white;">Click to Activate Your Account:</h3>
                <a href="{signup_link}" style="display: inline-block; background: white; color: #3D95CE; padding: 12px 24px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                    Activate Venmo Teen
                </a>
            </div>
            
            <h3>Why This is Better Than Apple Cash:</h3>
            <ul>
                <li>🎯 All your friends use Venmo</li>
                <li>💸 Split costs for food, movies, anything!</li>
                <li>📱 Works on any phone (when you eventually switch)</li>
                <li>🎮 Buy games and subscriptions easily</li>
                <li>📊 Track your spending with categories</li>
            </ul>
            
            <h3>Quick Setup (5 minutes):</h3>
            <ol>
                <li>Click the activation link above</li>
                <li>Create your username (make it cool!)</li>
                <li>Verify with the code I'll text you</li>
                <li>Start receiving your {allowance_amount}!</li>
            </ol>
            
            <p style="background: #fffacd; padding: 10px; border-radius: 5px;">
                <strong>Parent Note:</strong> I can see your transactions and set spending limits, but you have freedom to use it with friends!
            </p>
            
            <p>Let me know when you're set up and I'll send your first {allowance_amount}!</p>
            
            <p>- Dad</p>
        </body>
        </html>
        """
        
        text_body = f"""
Hey {teen_name}!

Your Venmo Teen account is ready! {excitement}

Your Allowance: {allowance_amount} for {allowance_reason}

Activate here: {signup_link}

Why it's better than Apple Cash:
- All your friends use it
- Split costs easily
- Works on any phone
- Track your spending

Quick setup:
1. Click the link
2. Create your username
3. Verify with the code
4. Get your {allowance_amount}!

- Dad
        """
        
        return {
            "html": html_body,
            "text": text_body
        }
    
    @staticmethod
    def life360_setup(
        recipient_name: str,
        invite_code: str,
        circle_name: str,
        relationship: str
    ) -> Dict[str, str]:
        """Generate Life360 setup instructions"""
        
        if relationship == "spouse":
            greeting = f"Hi {recipient_name},"
            benefit = "This is actually more accurate than Find My, and it works with my Android!"
        else:
            greeting = f"Hey {recipient_name}!"
            benefit = "This is like Find My but better - and it works with my new Android phone!"
        
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #7B4397;">Join Our Family Life360 Circle! 🗺️</h2>
            
            <p>{greeting}</p>
            
            <p>{benefit}</p>
            
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3>Family Circle: {circle_name}</h3>
                <p style="font-size: 24px; font-family: monospace; background: white; color: #764ba2; padding: 10px; border-radius: 5px; text-align: center;">
                    Invite Code: <strong>{invite_code}</strong>
                </p>
                <p style="font-size: 14px;">⏰ Code expires in 48 hours</p>
            </div>
            
            <h3>Why Life360 is Better Than Find My:</h3>
            <ul>
                <li>🎯 More accurate location tracking</li>
                <li>📱 Works across iPhone AND Android</li>
                <li>🚗 Driving reports and crash detection</li>
                <li>📍 Place alerts (know when kids arrive at school)</li>
                <li>💬 Built-in family chat</li>
                <li>🔋 Battery level monitoring</li>
            </ul>
            
            <h3>Setup Instructions (3 minutes):</h3>
            <ol>
                <li>Download Life360 from the App Store</li>
                <li>Create account with your phone number</li>
                <li>Select "Join a Circle"</li>
                <li>Enter code: <strong>{invite_code}</strong></li>
                <li>You're connected!</li>
            </ol>
            
            <p style="background: #f0f0f0; padding: 15px; border-radius: 5px;">
                <strong>Privacy Note:</strong> You control when location is shared. Set it to "Always" for family safety, or pause when you need privacy.
            </p>
            
            <p>This keeps our family connected and safe, no matter what phones we use!</p>
            
            <p>Love,<br>Dad</p>
        </body>
        </html>
        """
        
        text_body = f"""
{greeting}

{benefit}

Join our Life360 family circle: {circle_name}
Invite Code: {invite_code}
(Expires in 48 hours)

Why it's better than Find My:
- More accurate tracking
- Works on iPhone AND Android
- Driving reports
- Place alerts
- Family chat built-in

Setup:
1. Download Life360
2. Create account
3. Join circle with code: {invite_code}
4. You're connected!

Love,
Dad
        """
        
        return {
            "html": html_body,
            "text": text_body
        }
```

---

## 5. MCP Server Implementation

### 5.1 Gmail MCP Tools Server

```python
#!/usr/bin/env python3.11
"""
Gmail Tools MCP Server
Agent-orchestrated email sending for all family bridge services
"""

import asyncio
import logging
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from .gmail_client import GmailClient
from .email_templates import EmailTemplates

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("gmail-tools")
gmail_client = None

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Gmail tools"""
    return [
        types.Tool(
            name="send_family_emails",
            description="Send personalized setup emails to family members for any service (WhatsApp, Venmo Teen, Life360)",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "enum": ["whatsapp", "venmo_teen", "life360"],
                        "description": "Which service to send instructions for"
                    },
                    "recipients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "relationship": {
                                    "type": "string",
                                    "enum": ["spouse", "child", "parent", "other"]
                                }
                            },
                            "required": ["name", "email"]
                        },
                        "description": "List of family members to email"
                    },
                    "service_data": {
                        "type": "object",
                        "description": "Service-specific data (invite links, codes, etc.)"
                    }
                },
                "required": ["service", "recipients", "service_data"]
            }
        ),
        types.Tool(
            name="send_custom_email",
            description="Send a custom email with full control over content",
            inputSchema={
                "type": "object",
                "properties": {
                    "to_email": {"type": "string"},
                    "subject": {"type": "string"},
                    "body_html": {"type": "string"},
                    "body_text": {"type": "string"},
                    "cc_emails": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional CC recipients"
                    }
                },
                "required": ["to_email", "subject", "body_html"]
            }
        ),
        types.Tool(
            name="check_email_status",
            description="Check status of sent emails for a specific service",
            inputSchema={
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "description": "Service to check email status for"
                    },
                    "hours_back": {
                        "type": "integer",
                        "default": 24,
                        "description": "How many hours back to check"
                    }
                },
                "required": ["service"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle Gmail tool calls"""
    global gmail_client
    
    try:
        # Initialize Gmail client if needed
        if gmail_client is None:
            # Check for OAuth credentials
            creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
            if not creds_path:
                return [types.TextContent(
                    type="text",
                    text="❌ Please configure GMAIL_CREDENTIALS_PATH with your OAuth credentials file"
                )]
            
            gmail_client = GmailClient()
            await gmail_client.initialize()
        
        if name == "send_family_emails":
            return await handle_send_family_emails(arguments)
        
        elif name == "send_custom_email":
            return await handle_send_custom_email(arguments)
        
        elif name == "check_email_status":
            return await handle_check_email_status(arguments)
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Gmail tool execution error: {e}")
        return [types.TextContent(type="text", text=f"❌ Error: {str(e)}")]

async def handle_send_family_emails(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle sending family setup emails for various services"""
    
    service = arguments["service"]
    recipients = arguments["recipients"]
    service_data = arguments["service_data"]
    
    results = []
    
    # Get parent email for CC
    parent_email = os.getenv('PARENT_EMAIL', gmail_client.user_email)
    
    for recipient in recipients:
        try:
            # Generate appropriate template
            if service == "whatsapp":
                template = EmailTemplates.whatsapp_invite(
                    recipient_name=recipient["name"],
                    group_name=service_data.get("group_name", "Family Group"),
                    invite_link=service_data["invite_link"],
                    relationship=recipient.get("relationship", "family member")
                )
                subject = f"Join our family WhatsApp group - {service_data.get('group_name', 'Family Group')}"
                
            elif service == "venmo_teen":
                template = EmailTemplates.venmo_teen_instructions(
                    teen_name=recipient["name"],
                    signup_link=service_data["signup_link"],
                    allowance_amount=service_data.get("allowance_amount", "$25/month"),
                    allowance_reason=service_data.get("allowance_reason", "allowance"),
                    teen_age=service_data.get("teen_age", 15)
                )
                subject = "Your Venmo Teen account is ready!"
                
            elif service == "life360":
                template = EmailTemplates.life360_setup(
                    recipient_name=recipient["name"],
                    invite_code=service_data["invite_code"],
                    circle_name=service_data.get("circle_name", "Family Circle"),
                    relationship=recipient.get("relationship", "family member")
                )
                subject = f"Join our Life360 family circle - {service_data.get('circle_name', 'Family Circle')}"
                
            else:
                results.append({
                    "recipient": recipient["name"],
                    "status": "error",
                    "message": f"Unknown service: {service}"
                })
                continue
            
            # Determine CC list
            cc_list = None
            if service == "venmo_teen" and recipient.get("relationship") == "child":
                # CC parent on teen emails
                cc_list = [parent_email]
            
            # Send email
            result = await gmail_client.send_email(
                to_email=recipient["email"],
                subject=subject,
                body_html=template["html"],
                body_text=template["text"],
                cc_emails=cc_list,
                from_name="Dad (iOS→Android Migration)"
            )
            
            # Log service type
            await log_service_email(
                service=service,
                recipient_email=recipient["email"],
                recipient_name=recipient["name"],
                status=result["status"]
            )
            
            results.append({
                "recipient": recipient["name"],
                "email": recipient["email"],
                "status": result["status"],
                "message_id": result.get("message_id")
            })
            
        except Exception as e:
            logger.error(f"Failed to send email to {recipient['name']}: {e}")
            results.append({
                "recipient": recipient["name"],
                "status": "error",
                "message": str(e)
            })
    
    # Format response
    successful = [r for r in results if r["status"] == "sent"]
    failed = [r for r in results if r["status"] != "sent"]
    
    response = f"""📧 **Family Email Summary for {service.replace('_', ' ').title()}**

✅ **Sent Successfully: {len(successful)}/{len(results)}**"""
    
    for result in successful:
        response += f"\n  • {result['recipient']} ({result['email']})"
    
    if failed:
        response += f"\n\n❌ **Failed: {len(failed)}**"
        for result in failed:
            response += f"\n  • {result['recipient']}: {result.get('message', 'Unknown error')}"
    
    if service == "whatsapp":
        response += "\n\n📱 Each family member received personalized WhatsApp setup instructions with the group invite link."
    elif service == "venmo_teen":
        response += "\n\n💰 Teen received Venmo Teen activation link with parent CC'd for transparency."
    elif service == "life360":
        response += "\n\n🗺️ Family members received Life360 setup instructions with the invite code."
    
    return [types.TextContent(type="text", text=response)]

async def handle_send_custom_email(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle sending custom emails"""
    
    result = await gmail_client.send_email(
        to_email=arguments["to_email"],
        subject=arguments["subject"],
        body_html=arguments["body_html"],
        body_text=arguments.get("body_text"),
        cc_emails=arguments.get("cc_emails"),
        from_name="iOS→Android Migration Assistant"
    )
    
    if result["status"] == "sent":
        response = f"""✅ Custom email sent successfully!
        
To: {arguments['to_email']}
Subject: {arguments['subject']}
Message ID: {result['message_id']}"""
        
        if arguments.get("cc_emails"):
            response += f"\nCC: {', '.join(arguments['cc_emails'])}"
    else:
        response = f"""❌ Failed to send custom email
        
To: {arguments['to_email']}
Error: {result.get('message', 'Unknown error')}"""
    
    return [types.TextContent(type="text", text=response)]

async def handle_check_email_status(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Check email status for a service"""
    
    service = arguments["service"]
    hours_back = arguments.get("hours_back", 24)
    
    try:
        import duckdb
        from datetime import datetime, timedelta
        
        db_path = os.getenv('DUCKDB_PATH', './data/photo_migration.db')
        conn = duckdb.connect(db_path)
        
        cutoff_time = datetime.now() - timedelta(hours=hours_back)
        
        results = conn.execute("""
            SELECT to_email, subject, sent_at, status
            FROM email_logs
            WHERE service_type = ? AND sent_at > ?
            ORDER BY sent_at DESC
        """, [service, cutoff_time]).fetchall()
        
        conn.close()
        
        if not results:
            response = f"No emails found for {service} in the last {hours_back} hours"
        else:
            response = f"""📧 **Email Status for {service.replace('_', ' ').title()}**
Last {hours_back} hours:

"""
            for email in results:
                status_emoji = "✅" if email[3] == "sent" else "❌"
                response += f"{status_emoji} {email[0]} - {email[1][:50]}... ({email[2].strftime('%Y-%m-%d %H:%M')})\n"
        
        return [types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Failed to check email status: {e}")
        return [types.TextContent(
            type="text",
            text=f"❌ Error checking email status: {str(e)}"
        )]

async def log_service_email(
    service: str,
    recipient_email: str,
    recipient_name: str,
    status: str
):
    """Log service-specific email to database"""
    try:
        import duckdb
        from datetime import datetime
        
        db_path = os.getenv('DUCKDB_PATH', './data/photo_migration.db')
        conn = duckdb.connect(db_path)
        
        # Update service-specific tables
        if service == "whatsapp":
            conn.execute("""
                UPDATE whatsapp_members 
                SET invite_sent_at = ?, status = 'invited'
                WHERE member_email = ?
            """, [datetime.now(), recipient_email])
            
        elif service == "venmo_teen":
            conn.execute("""
                UPDATE venmo_teen_accounts
                SET instructions_sent_at = ?, status = 'instructions_sent'
                WHERE teen_email = ?
            """, [datetime.now(), recipient_email])
            
        elif service == "life360":
            conn.execute("""
                UPDATE life360_members
                SET invite_sent_at = ?, status = 'invited'
                WHERE member_email = ?
            """, [datetime.now(), recipient_email])
        
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to log service email: {e}")

async def main():
    """Main entry point"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Gmail Tools MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="gmail-tools",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 6. Database Schema

### 6.1 Email Tracking Tables

```sql
-- Add to existing photo_migration.db

-- General email log
CREATE TABLE IF NOT EXISTS email_logs (
    id INTEGER PRIMARY KEY,
    to_email VARCHAR,
    subject VARCHAR,
    service_type VARCHAR, -- 'whatsapp', 'venmo_teen', 'life360', 'custom'
    message_id VARCHAR,
    sent_at TIMESTAMP,
    status VARCHAR, -- 'sent', 'failed', 'bounced'
    error_message TEXT
);

-- Service-specific tracking updated by email sends
-- (These tables are created by respective services)

-- Index for efficient queries
CREATE INDEX IF NOT EXISTS idx_email_logs_service ON email_logs(service_type, sent_at);
CREATE INDEX IF NOT EXISTS idx_email_logs_recipient ON email_logs(to_email);
```

---

## 7. Error Handling

### 7.1 Gmail-Specific Error Handling

```python
class GmailError(Exception):
    """Base Gmail error"""
    pass

class GmailAuthError(GmailError):
    """OAuth authentication failed"""
    pass

class GmailQuotaError(GmailError):
    """Gmail API quota exceeded"""
    pass

class GmailInvalidRecipientError(GmailError):
    """Invalid recipient email"""
    pass

async def handle_gmail_errors(func):
    """Decorator for Gmail error handling"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except HttpError as e:
            if e.resp.status == 401:
                raise GmailAuthError("Gmail authentication failed - token may be expired")
            elif e.resp.status == 429:
                raise GmailQuotaError("Gmail API quota exceeded - try again later")
            elif e.resp.status == 400:
                raise GmailInvalidRecipientError(f"Invalid email recipient: {str(e)}")
            else:
                raise GmailError(f"Gmail API error: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected Gmail error: {e}")
            raise
    return wrapper
```

---

## 8. Configuration & Environment

### 8.1 Environment Variables

```bash
# Gmail OAuth configuration (REQUIRED)
GMAIL_CREDENTIALS_PATH=./credentials/gmail_creds.json

# Optional settings
PARENT_EMAIL=george.vetticaden@gmail.com  # For CC on teen emails
GMAIL_TOKEN_PATH=~/.gmail_token/token.json

# Database (shared with other tools)
DUCKDB_PATH=./data/photo_migration.db

# Email settings
MAX_EMAILS_PER_MINUTE=20
EMAIL_RETRY_ATTEMPTS=3
```

### 8.2 OAuth Setup Instructions

```markdown
## Gmail OAuth Setup (One-Time)

1. **Google Cloud Console Setup:**
   - Go to https://console.cloud.google.com
   - Create new project or select existing
   - Enable Gmail API
   - Create OAuth 2.0 credentials (Desktop application)
   - Download credentials JSON

2. **Configure Environment:**
   ```bash
   export GMAIL_CREDENTIALS_PATH=./credentials/gmail_creds.json
   ```

3. **Run OAuth Setup:**
   ```bash
   python setup_oauth.py
   ```
   - Browser will open for authorization
   - Grant permissions for Gmail send/read
   - Token saved to ~/.gmail_token/token.json

4. **Test:**
   ```bash
   python test_gmail.py
   ```
```

---

## 9. Testing Requirements

### 9.1 Gmail Module Testing

```python
# test_gmail.py
import asyncio
import os
from gmail_client import GmailClient
from email_templates import EmailTemplates

async def test_oauth_setup():
    """Test OAuth authentication"""
    assert os.getenv('GMAIL_CREDENTIALS_PATH'), "GMAIL_CREDENTIALS_PATH not set"
    
    client = GmailClient()
    await client.initialize()
    
    print(f"✅ Authenticated as: {client.user_email}")

async def test_send_test_email():
    """Test sending a simple email"""
    client = GmailClient()
    await client.initialize()
    
    result = await client.send_email(
        to_email=client.user_email,  # Send to self
        subject="Gmail Tools Test",
        body_html="<h1>Test Successful!</h1><p>Gmail tools are working.</p>",
        body_text="Test Successful! Gmail tools are working."
    )
    
    assert result["status"] == "sent"
    print(f"✅ Test email sent: {result['message_id']}")

async def test_family_templates():
    """Test all family email templates"""
    
    # Test WhatsApp template
    whatsapp = EmailTemplates.whatsapp_invite(
        recipient_name="Test User",
        group_name="Test Family",
        invite_link="https://chat.whatsapp.com/test",
        relationship="child"
    )
    assert "Join Our Family WhatsApp Group" in whatsapp["html"]
    
    # Test Venmo Teen template
    venmo = EmailTemplates.venmo_teen_instructions(
        teen_name="Test Teen",
        signup_link="https://venmo.com/test",
        allowance_amount="$25/month",
        allowance_reason="testing",
        teen_age=15
    )
    assert "Venmo Teen Account" in venmo["html"]
    
    # Test Life360 template
    life360 = EmailTemplates.life360_setup(
        recipient_name="Test User",
        invite_code="TST-123",
        circle_name="Test Circle",
        relationship="spouse"
    )
    assert "Life360" in life360["html"]
    
    print("✅ All email templates validated")

if __name__ == "__main__":
    asyncio.run(test_oauth_setup())
    asyncio.run(test_send_test_email())
    asyncio.run(test_family_templates())
```

---

## 10. Demo Integration

### 10.1 Expected Tool Calls in Demo

**WhatsApp Email Send (Act 4):**
```json
{
  "service": "whatsapp",
  "recipients": [
    {"name": "Jaisy", "email": "jcvetticaden@gmail.com", "relationship": "spouse"},
    {"name": "Laila", "email": "lailarvett@gmail.com", "relationship": "child"},
    {"name": "Ethan", "email": "ethanjvett@gmail.com", "relationship": "child"},
    {"name": "Maya", "email": "mayatvett@gmail.com", "relationship": "child"}
  ],
  "service_data": {
    "group_name": "Vetticaden Family Chat",
    "invite_link": "https://chat.whatsapp.com/BQdX7R9kT5LHV8z4..."
  }
}
```

**Venmo Teen Email Send (Act 5):**
```json
{
  "service": "venmo_teen",
  "recipients": [
    {"name": "Ethan", "email": "ethanjvett@gmail.com", "relationship": "child"}
  ],
  "service_data": {
    "signup_link": "https://get.venmo.com/teen-signup/ETH4N-X7Y9Z",
    "allowance_amount": "$25/month",
    "allowance_reason": "mowing the lawn",
    "teen_age": 15
  }
}
```

**Life360 Email Send (Act 6):**
```json
{
  "service": "life360",
  "recipients": [
    {"name": "Jaisy", "email": "jcvetticaden@gmail.com", "relationship": "spouse"},
    {"name": "Laila", "email": "lailarvett@gmail.com", "relationship": "child"},
    {"name": "Ethan", "email": "ethanjvett@gmail.com", "relationship": "child"},
    {"name": "Maya", "email": "mayatvett@gmail.com", "relationship": "child"}
  ],
  "service_data": {
    "circle_name": "Vetticaden Family",
    "invite_code": "INJ-JOQ"
  }
}
```

### 10.2 Demo Success Criteria

- ✅ **OAuth Working**: Gmail authenticated via OAuth, not passwords
- ✅ **All Templates Sent**: WhatsApp, Venmo Teen, Life360 emails delivered
- ✅ **Personalization**: Each family member gets age/relationship-appropriate content
- ✅ **Parent Transparency**: Parent CC'd on teen emails
- ✅ **Status Tracking**: All emails logged to database

---

## 11. Community Reusability

### 11.1 Setup Documentation

```markdown
# Gmail Tools Setup

## Prerequisites
- Google Cloud account (free tier works)
- Gmail account
- Python 3.11+
- Claude Desktop with MCP tools

## Quick Start
1. Set up Google Cloud OAuth credentials
2. Download credentials JSON
3. Set GMAIL_CREDENTIALS_PATH environment variable
4. Run setup_oauth.py for one-time authorization
5. Ready to send family emails!

## Usage
The agent orchestrates all email sending:
- WhatsApp invites after group creation
- Venmo Teen instructions after account setup
- Life360 setup after code generation
- Custom emails for any other needs
```

### 11.2 Troubleshooting Guide

- **OAuth Error**: Re-run setup_oauth.py to refresh token
- **Quota Exceeded**: Gmail has daily limits (500 for free accounts)
- **Invalid Recipient**: Verify email addresses are correct
- **Template Issues**: Check service_data has all required fields

---

## 12. Success Criteria

### 12.1 Technical Success
- ✅ **OAuth Authentication**: No passwords, secure token management
- ✅ **Template System**: Service-specific, personalized emails
- ✅ **Agent Orchestration**: Agent controls all email sends
- ✅ **Error Handling**: Graceful failures with clear messages
- ✅ **Status Tracking**: Database logging for all emails

### 12.2 Demo Success  
- ✅ **Just-in-Time Auth**: OAuth check only when first email sent
- ✅ **Family Personalization**: Each member gets appropriate content
- ✅ **Service Separation**: Clear distinction between services
- ✅ **Parent Visibility**: CC on teen communications
- ✅ **Delivery Confirmation**: Real emails sent and tracked

### 12.3 Community Success
- ✅ **Easy OAuth Setup**: One-time configuration with clear guide
- ✅ **Service Agnostic**: Works for any family bridge service
- ✅ **Template Extensibility**: Easy to add new services
- ✅ **Reliable Delivery**: Gmail API ensures high deliverability

This comprehensive Gmail Tools Module provides the agent with complete control over family email orchestration, enabling personalized communication for all migration services while maintaining security through OAuth authentication.
                    