# WhatsApp Automation - Complete Requirements Document
## Family Communication Bridge via Web.WhatsApp.com Automation

### Project Context
This document specifies requirements for automating WhatsApp family group creation to replace iMessage when one family member switches from iPhone to Android. The solution uses browser automation via Playwright to handle the complete WhatsApp Web workflow, from authentication to group creation and invite link generation. The agent orchestrates email sending separately through the Gmail tools module.

**CRITICAL**: All authentication credentials are retrieved from environment variables within the MCP tools. Credentials are NEVER passed as parameters from Claude Desktop for security reasons.

---

## 1. Project Structure & Integration

### 1.1 MCP Tool Architecture
```
mcp-tools/
├── whatsapp-automation/
│   ├── src/whatsapp_automation/
│   │   ├── __init__.py
│   │   ├── whatsapp_client.py       # Main automation client
│   │   ├── session_manager.py       # Session persistence
│   │   ├── group_manager.py         # Group creation logic
│   │   ├── invite_manager.py        # Invite link generation
│   │   ├── server.py                # MCP server implementation
│   │   └── recorder.py              # Flow recording utility
│   ├── test_whatsapp.py             # Standalone testing
│   ├── record_whatsapp_flow.py      # Browser flow recorder
│   ├── pyproject.toml
│   ├── .env
│   └── README.md
```

### 1.2 Integration with Existing Tools
- **Database**: Shares DuckDB with photo-migration tools
- **Session Pattern**: Follows same session persistence as icloud_client.py
- **MCP Server**: Independent server that can run alongside photo-migration
- **Email Integration**: Agent orchestrates email sending via separate Gmail tools module

---

## 2. WhatsApp Web Automation Requirements

### 2.1 Flow Recording First (Development Phase)

**CRITICAL**: Before implementing automation, use record_whatsapp_flow.py to capture the complete workflow:

```python
# record_whatsapp_flow.py - Based on existing record_flow.py pattern

class WhatsAppFlowRecorder:
    """Record WhatsApp Web automation workflow for development"""
    
    def __init__(self):
        self.steps = []
        self.screenshot_dir = "./flow_recordings/whatsapp"
        os.makedirs(self.screenshot_dir, exist_ok=True)
    
    async def record_complete_flow(self):
        """Record the complete WhatsApp Web workflow"""
        
        print("=" * 80)
        print("WHATSAPP WEB FLOW RECORDER")
        print("Complete these steps manually while recording:")
        print("1. Navigate to web.whatsapp.com")
        print("2. Click 'Log in with phone number'")
        print("3. Enter phone number and click Next")
        print("4. Enter SMS verification code")
        print("5. Navigate to group creation")
        print("6. Create new group")
        print("7. Generate invite link")
        print("Press ENTER after each major step")
        print("Type 'done' when complete")
        print("=" * 80)
        
        playwright = await async_playwright().start()
        browser = await playwright.chromium.launch(headless=False)
        page = await browser.new_page()
        
        await page.goto("https://web.whatsapp.com")
        
        step_num = 1
        while True:
            user_input = input(f"\nStep {step_num} - Press ENTER after action (or 'done'): ")
            
            if user_input.lower() == 'done':
                break
            
            # Capture current state
            step_data = await self._capture_page_state(page, step_num)
            self.steps.append(step_data)
            print(f"✓ Captured step {step_num}: {step_data['title']}")
            step_num += 1
        
        # Save recording
        await self._save_recording()
        await browser.close()
        await playwright.stop()
```

### 2.2 Main WhatsApp Client Implementation

```python
class WhatsAppWebClient:
    """WhatsApp Web automation client with session persistence"""
    
    def __init__(self, session_dir: Optional[str] = None):
        self.playwright = None
        self.browser = None
        self.page = None
        
        # Session management (same pattern as icloud_client.py)
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            # Get from environment or use default
            session_dir = os.getenv('WHATSAPP_SESSION_DIR', '~/.whatsapp_session')
            self.session_dir = Path(os.path.expanduser(session_dir))
        
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "whatsapp_state.json"
        self.session_info_file = self.session_dir / "session_info.json"
        
        logger.info(f"WhatsApp session directory: {self.session_dir}")
    
    async def initialize(self):
        """Initialize Playwright"""
        self.playwright = await async_playwright().start()
    
    def is_session_valid(self) -> bool:
        """Check if saved WhatsApp session exists and is recent"""
        if not self.session_file.exists() or not self.session_info_file.exists():
            return False
        
        try:
            with open(self.session_info_file, 'r') as f:
                info = json.load(f)
            
            # WhatsApp Web sessions last ~7 days
            saved_time = datetime.fromisoformat(info['saved_at'])
            age = datetime.now() - saved_time
            
            if age > timedelta(days=6):  # Refresh before 7 day limit
                logger.info(f"WhatsApp session is {age.days} days old, will need fresh login")
                return False
            
            logger.info(f"Found valid WhatsApp session from {saved_time.strftime('%Y-%m-%d %H:%M')}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking WhatsApp session: {e}")
            return False
    
    async def authenticate(self, force_fresh_login: bool = False) -> Dict[str, Any]:
        """
        Authenticate with WhatsApp Web
        Phone number is ALWAYS retrieved from environment variables
        Shows FULL authentication flow for demo (including SMS verification)
        """
        # Get phone number from environment
        phone_number = os.getenv('WHATSAPP_PHONE_NUMBER')
        if not phone_number:
            return {
                "status": "error",
                "message": "Please configure WHATSAPP_PHONE_NUMBER in your environment variables"
            }
        
        try:
            use_saved_session = self.is_session_valid() and not force_fresh_login
            
            if use_saved_session:
                logger.info("Using saved WhatsApp session...")
                self.browser = await self.playwright.chromium.launch(
                    headless=False,
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                context = await self.browser.new_context(
                    storage_state=str(self.session_file),
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
            else:
                logger.info("Starting fresh WhatsApp login...")
                self.browser = await self.playwright.chromium.launch(
                    headless=False,  # Always visible for demo
                    args=['--disable-blink-features=AutomationControlled']
                )
                
                context = await self.browser.new_context(
                    viewport={"width": 1920, "height": 1080},
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                )
            
            self.page = await context.new_page()
            
            # Navigate to WhatsApp Web
            logger.info("Navigating to web.whatsapp.com...")
            await self.page.goto("https://web.whatsapp.com", wait_until="networkidle")
            await self.page.wait_for_timeout(3000)
            
            # Check if already logged in
            if await self._is_logged_in():
                logger.info("✅ Already logged into WhatsApp Web!")
                return {
                    "status": "already_authenticated",
                    "method": "saved_session",
                    "session_used": True
                }
            
            # Perform authentication workflow with phone from environment
            return await self._perform_authentication(phone_number)
            
        except Exception as e:
            logger.error(f"WhatsApp authentication failed: {e}")
            return {
                "status": "error",
                "message": f"Authentication failed: {str(e)}"
            }
    
    async def _perform_authentication(self, phone_number: str) -> Dict[str, Any]:
        """Complete authentication workflow based on recorded flow"""
        
        # Step 1: Click "Log in with phone number" (if available)
        phone_login_selectors = [
            'text="Log in with phone number"',
            '[data-testid="phone-number-login"]',
            'button:has-text("phone number")'
        ]
        
        phone_login_clicked = False
        for selector in phone_login_selectors:
            phone_login = await self.page.query_selector(selector)
            if phone_login:
                logger.info("Clicking 'Log in with phone number'...")
                await phone_login.click()
                await self.page.wait_for_timeout(2000)
                phone_login_clicked = True
                break
        
        if not phone_login_clicked:
            logger.info("Phone login option not found, continuing with QR code flow...")
        
        # Step 2: Enter phone number if phone login was clicked
        if phone_login_clicked:
            phone_selectors = [
                'input[type="tel"]',
                'input[aria-label*="phone"]',
                '[data-testid="phone-number-input"]'
            ]
            
            phone_field = None
            for selector in phone_selectors:
                phone_field = await self.page.query_selector(selector)
                if phone_field:
                    break
            
            if phone_field:
                logger.info(f"Entering phone number: {phone_number[:6]}****")
                await phone_field.click()
                await self.page.wait_for_timeout(500)
                await phone_field.fill(phone_number)
                
                # Click Next button
                next_selectors = [
                    'button:has-text("Next")',
                    '[data-testid="next-button"]',
                    'button[type="submit"]'
                ]
                
                for selector in next_selectors:
                    next_btn = await self.page.query_selector(selector)
                    if next_btn:
                        logger.info("Clicking Next...")
                        await next_btn.click()
                        break
            
            # Step 3: Handle SMS verification
            await self.page.wait_for_timeout(3000)
            
            # Look for verification code input
            code_selectors = [
                '[aria-label*="digit"]',
                'input[type="tel"][maxlength="1"]',
                '[data-testid="code-input"]'
            ]
            
            verification_found = False
            for selector in code_selectors:
                code_input = await self.page.query_selector(selector)
                if code_input:
                    verification_found = True
                    break
            
            if verification_found:
                logger.info("=" * 60)
                logger.info("📱 WhatsApp SMS Verification Required")
                logger.info("Check your phone for the 6-digit verification code")
                logger.info("Enter it in the browser when prompted")
                logger.info("This is LIVE authentication - real SMS required!")
                logger.info("=" * 60)
                
                # Wait for user to complete verification (up to 3 minutes)
                for i in range(36):  # 36 * 5 seconds = 3 minutes
                    await self.page.wait_for_timeout(5000)
                    
                    if await self._is_logged_in():
                        logger.info("✅ SMS verification completed successfully!")
                        await self._save_session()
                        return {
                            "status": "authenticated",
                            "method": "sms_verification",
                            "session_saved": True
                        }
                    
                    if i % 4 == 0:  # Every 20 seconds
                        logger.info(f"Waiting for SMS verification... ({(i+1)*5} seconds elapsed)")
                
                raise Exception("SMS verification timeout - please try again")
        
        # QR code fallback
        logger.info("Using QR code authentication...")
        logger.info("Scan the QR code with your phone's WhatsApp...")
        
        # Wait for QR code scan
        for i in range(24):  # 2 minutes
            await self.page.wait_for_timeout(5000)
            
            if await self._is_logged_in():
                logger.info("✅ QR code verification completed!")
                await self._save_session()
                return {
                    "status": "authenticated",
                    "method": "qr_code",
                    "session_saved": True
                }
            
            if i % 4 == 0:
                logger.info(f"Waiting for QR scan... ({(i+1)*5} seconds elapsed)")
        
        raise Exception("QR code verification timeout")
    
    async def _is_logged_in(self) -> bool:
        """Check if successfully logged into WhatsApp Web"""
        logged_in_selectors = [
            '[data-testid="chat-list"]',
            '[data-testid="side"]',
            'div[title="Chats"]',
            '[aria-label="Chat list"]'
        ]
        
        for selector in logged_in_selectors:
            element = await self.page.query_selector(selector)
            if element:
                return True
        
        return False
    
    async def _save_session(self):
        """Save WhatsApp session state"""
        try:
            context = self.browser.contexts[0]
            await context.storage_state(path=str(self.session_file))
            
            info = {
                'saved_at': datetime.now().isoformat(),
                'browser': 'chromium',
                'url': self.page.url,
                'title': await self.page.title()
            }
            
            with open(self.session_info_file, 'w') as f:
                json.dump(info, f, indent=2)
            
            logger.info("WhatsApp session saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save WhatsApp session: {e}")
```

### 2.3 Group Creation & Management

```python
class WhatsAppGroupManager:
    """Handle WhatsApp group creation and management"""
    
    def __init__(self, page):
        self.page = page
    
    async def create_family_group(
        self,
        group_name: str = "Family Group",
        group_description: str = "iOS to Android family bridge - better than iMessage!"
    ) -> Dict[str, Any]:
        """
        Create WhatsApp family group and return invite link
        Note: Email sending is handled separately by the agent using Gmail tools
        """
        
        try:
            # Ensure we're logged in
            if not await self._is_on_main_interface():
                raise Exception("Not logged into WhatsApp Web")
            
            # Step 1: Open menu (three dots or menu button)
            menu_selectors = [
                '[data-testid="menu"]',
                '[aria-label="Menu"]',
                'div[title="Menu"]',
                'button[aria-label="Menu"]'
            ]
            
            menu_clicked = False
            for selector in menu_selectors:
                menu_btn = await self.page.query_selector(selector)
                if menu_btn:
                    logger.info("Opening WhatsApp menu...")
                    await menu_btn.click()
                    await self.page.wait_for_timeout(1000)
                    menu_clicked = True
                    break
            
            if not menu_clicked:
                raise Exception("Could not find WhatsApp menu button")
            
            # Step 2: Click "New group"
            new_group_selectors = [
                'text="New group"',
                '[data-testid="new-group"]',
                'div:has-text("New group")',
                '[aria-label*="New group"]'
            ]
            
            group_clicked = False
            for selector in new_group_selectors:
                new_group = await self.page.query_selector(selector)
                if new_group:
                    logger.info("Clicking 'New group'...")
                    await new_group.click()
                    await self.page.wait_for_timeout(2000)
                    group_clicked = True
                    break
            
            if not group_clicked:
                raise Exception("Could not find 'New group' option")
            
            # Step 3: Skip contact selection (we'll use invite link)
            skip_selectors = [
                '[data-testid="next"]',
                'button:has-text("Next")',
                'button:has-text("Skip")',
                '[aria-label*="Next"]'
            ]
            
            for selector in skip_selectors:
                skip_btn = await self.page.query_selector(selector)
                if skip_btn:
                    logger.info("Skipping contact selection...")
                    await skip_btn.click()
                    await self.page.wait_for_timeout(2000)
                    break
            
            # Step 4: Enter group name and description
            await self._set_group_details(group_name, group_description)
            
            # Step 5: Create the group
            create_selectors = [
                '[data-testid="group-create"]',
                'button:has-text("Create")',
                'button[type="submit"]',
                '[aria-label*="Create"]'
            ]
            
            for selector in create_selectors:
                create_btn = await self.page.query_selector(selector)
                if create_btn:
                    logger.info("Creating group...")
                    await create_btn.click()
                    await self.page.wait_for_timeout(3000)
                    break
            
            # Step 6: Generate invite link
            invite_link = await self._generate_invite_link()
            
            # Save to database
            await self._save_group_to_db(group_name, group_description, invite_link)
            
            return {
                "status": "created",
                "group_name": group_name,
                "description": group_description,
                "invite_link": invite_link,
                "created_at": datetime.now().isoformat(),
                "members_count": 1  # Just creator initially
            }
            
        except Exception as e:
            logger.error(f"Group creation failed: {e}")
            return {
                "status": "error",
                "message": f"Group creation failed: {str(e)}"
            }
    
    async def _save_group_to_db(self, name: str, description: str, invite_link: str):
        """Save group information to database"""
        try:
            import duckdb
            db_path = os.getenv('DUCKDB_PATH', './data/photo_migration.db')
            conn = duckdb.connect(db_path)
            
            phone_number = os.getenv('WHATSAPP_PHONE_NUMBER')
            
            conn.execute("""
                INSERT INTO whatsapp_groups 
                (group_name, group_description, invite_link, created_at, creator_phone, status, member_count)
                VALUES (?, ?, ?, ?, ?, 'created', 1)
            """, [name, description, invite_link, datetime.now(), phone_number])
            
            conn.close()
            logger.info(f"Group '{name}' saved to database")
            
        except Exception as e:
            logger.error(f"Failed to save group to database: {e}")
```

---

## 3. MCP Server Integration

### 3.1 WhatsApp MCP Tools

```python
#!/usr/bin/env python3.11
"""
WhatsApp Automation MCP Server
Creates groups and returns invite links - email sending handled by agent
"""

import asyncio
import logging
import os
from typing import Any, Dict
from dotenv import load_dotenv
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from .whatsapp_client import WhatsAppWebClient
from .group_manager import WhatsAppGroupManager

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("whatsapp-automation")
whatsapp_client = None

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available WhatsApp automation tools"""
    return [
        types.Tool(
            name="setup_whatsapp_group",
            description="Create WhatsApp family group and return invite link. Phone number retrieved from WHATSAPP_PHONE_NUMBER environment variable.",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string", 
                        "default": "Family Group",
                        "description": "Name for the WhatsApp family group"
                    },
                    "group_description": {
                        "type": "string",
                        "default": "iOS to Android family bridge - better than iMessage!",
                        "description": "Description for the family group"
                    },
                    "family_members": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "relationship": {"type": "string"}
                            }
                        },
                        "description": "Family members info for tracking (emails sent separately)"
                    }
                },
                "required": []  # No required fields - all have defaults or are optional
            }
        ),
        types.Tool(
            name="check_whatsapp_status",
            description="Check WhatsApp group status and member adoption",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {"type": "string"}
                },
                "required": ["group_name"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle WhatsApp automation tool calls"""
    global whatsapp_client
    
    try:
        if name == "setup_whatsapp_group":
            # Check for phone number in environment
            phone_number = os.getenv('WHATSAPP_PHONE_NUMBER')
            if not phone_number:
                return [types.TextContent(
                    type="text",
                    text="❌ To authenticate with WhatsApp, please ensure WHATSAPP_PHONE_NUMBER is configured in your environment variables."
                )]
            
            # Initialize client
            if whatsapp_client is None:
                session_dir = os.getenv('WHATSAPP_SESSION_DIR', '~/.whatsapp_session')
                whatsapp_client = WhatsAppWebClient(session_dir=session_dir)
                await whatsapp_client.initialize()
            
            group_name = arguments.get("group_name", "Family Group")
            group_description = arguments.get("group_description", "iOS to Android family bridge - better than iMessage!")
            family_members = arguments.get("family_members", [])
            
            # Step 1: Authenticate with WhatsApp Web (uses env variable internally)
            auth_result = await whatsapp_client.authenticate()
            
            if auth_result.get("status") == "error":
                return [types.TextContent(
                    type="text",
                    text=f"❌ WhatsApp authentication failed: {auth_result.get('message', 'Unknown error')}"
                )]
            
            # Step 2: Create family group
            group_manager = WhatsAppGroupManager(whatsapp_client.page)
            group_result = await group_manager.create_family_group(group_name, group_description)
            
            if group_result.get("status") == "error":
                return [types.TextContent(
                    type="text",
                    text=f"❌ Group creation failed: {group_result.get('message', 'Unknown error')}"
                )]
            
            # Step 3: Store family member info in database for tracking
            if family_members:
                await store_family_members(group_result, family_members)
            
            # Format response (agent will handle email sending separately)
            response = f"""✅ WhatsApp Family Group Created Successfully!

📱 **Group Details:**
- Name: {group_result['group_name']}
- Description: {group_result['description']}
- Created: {group_result['created_at']}

🔗 **Invite Link:**
{group_result['invite_link']}

The group is ready! You can now send this invite link to your family members.
"""
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "check_whatsapp_status":
            group_name = arguments["group_name"]
            
            # Check database for group status
            status = await check_group_status(group_name)
            
            response = f"""📊 WhatsApp Group Status: {group_name}

{status}

Note: For real-time member activity, check the WhatsApp group directly.
"""
            
            return [types.TextContent(type="text", text=response)]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"WhatsApp tool execution error: {e}")
        return [types.TextContent(type="text", text=f"❌ Error: {str(e)}")]

async def store_family_members(group_result: Dict, family_members: list):
    """Store family member information for tracking"""
    try:
        import duckdb
        db_path = os.getenv('DUCKDB_PATH', './data/photo_migration.db')
        conn = duckdb.connect(db_path)
        
        # Get group ID
        group_id = conn.execute("""
            SELECT id FROM whatsapp_groups 
            WHERE group_name = ? AND invite_link = ?
        """, [group_result['group_name'], group_result['invite_link']]).fetchone()[0]
        
        # Insert family members
        for member in family_members:
            conn.execute("""
                INSERT INTO whatsapp_members 
                (group_id, member_name, member_email, relationship, invite_sent_at, status)
                VALUES (?, ?, ?, ?, NULL, 'pending')
            """, [group_id, member['name'], member['email'], member['relationship']])
        
        conn.close()
        logger.info(f"Stored {len(family_members)} family members for tracking")
        
    except Exception as e:
        logger.error(f"Failed to store family members: {e}")

async def check_group_status(group_name: str) -> str:
    """Check group status from database"""
    try:
        import duckdb
        db_path = os.getenv('DUCKDB_PATH', './data/photo_migration.db')
        conn = duckdb.connect(db_path)
        
        # Get group info
        group = conn.execute("""
            SELECT status, member_count, created_at, invite_link
            FROM whatsapp_groups 
            WHERE group_name = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, [group_name]).fetchone()
        
        if not group:
            return "Group not found in database"
        
        # Get member status
        members = conn.execute("""
            SELECT member_name, relationship, status
            FROM whatsapp_members 
            WHERE group_id = (
                SELECT id FROM whatsapp_groups WHERE group_name = ? LIMIT 1
            )
        """, [group_name]).fetchall()
        
        conn.close()
        
        status_text = f"""Group Status: {group[0]}
Created: {group[2]}
Member Count: {group[1]}

Family Members:"""
        
        for member in members:
            emoji = "✅" if member[2] == "joined" else "⏳"
            status_text += f"\n{emoji} {member[0]} ({member[1]}): {member[2]}"
        
        return status_text
        
    except Exception as e:
        logger.error(f"Failed to check group status: {e}")
        return f"Error checking status: {str(e)}"

async def main():
    """Main entry point"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("WhatsApp Automation MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="whatsapp-automation",
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

## 4. Database Integration

### 4.1 WhatsApp State Tracking (Extends photo-migration DuckDB)

```sql
-- Add to existing photo_migration.db

-- WhatsApp services table
CREATE TABLE IF NOT EXISTS whatsapp_groups (
    id INTEGER PRIMARY KEY,
    group_name VARCHAR,
    group_description VARCHAR,
    invite_link VARCHAR,
    created_at TIMESTAMP,
    creator_phone VARCHAR,
    status VARCHAR, -- 'created', 'active', 'archived'
    member_count INTEGER DEFAULT 1
);

-- WhatsApp member tracking
CREATE TABLE IF NOT EXISTS whatsapp_members (
    id INTEGER PRIMARY KEY,
    group_id INTEGER,
    member_name VARCHAR,
    member_email VARCHAR,
    relationship VARCHAR, -- 'spouse', 'child', 'parent'
    invite_sent_at TIMESTAMP,
    joined_at TIMESTAMP,
    status VARCHAR, -- 'pending', 'invited', 'joined', 'active'
    FOREIGN KEY (group_id) REFERENCES whatsapp_groups(id)
);
```

---

## 5. Error Handling & Resilience

### 5.1 WhatsApp-Specific Error Handling

```python
class WhatsAppError(Exception):
    """Base WhatsApp automation error"""
    pass

class WhatsAppAuthError(WhatsAppError):
    """WhatsApp authentication failed"""
    pass

class WhatsAppRateLimitError(WhatsAppError):
    """WhatsApp rate limiting detected"""
    pass

class WhatsAppSessionExpiredError(WhatsAppError):
    """WhatsApp session expired"""
    pass

# Retry logic for WhatsApp operations
async def retry_whatsapp_operation(operation, max_retries=3):
    """Retry WhatsApp operations with smart backoff"""
    for attempt in range(max_retries):
        try:
            return await operation()
        except WhatsAppRateLimitError:
            wait_time = (2 ** attempt) * 60  # 1, 2, 4 minutes
            logger.warning(f"WhatsApp rate limited, waiting {wait_time} seconds...")
            await asyncio.sleep(wait_time)
        except WhatsAppSessionExpiredError:
            logger.info("WhatsApp session expired, re-authenticating...")
            break
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"WhatsApp operation attempt {attempt + 1} failed: {e}")
            await asyncio.sleep(5)
```

---

## 6. Configuration & Environment

### 6.1 Environment Variables

```bash
# WhatsApp configuration (REQUIRED)
WHATSAPP_PHONE_NUMBER=+16147912019

# Optional settings
WHATSAPP_SESSION_DIR=~/.whatsapp_session
SCREENSHOT_DIR=./screenshots/whatsapp

# Database (shared with photo-migration)
DUCKDB_PATH=./data/photo_migration.db

# Demo settings
DEMO_MODE=false
```

---

## 7. Testing Requirements

### 7.1 Development Testing

```python
# test_whatsapp.py
async def test_authentication():
    """Test WhatsApp Web authentication flow"""
    # Ensure environment variable is set
    assert os.getenv('WHATSAPP_PHONE_NUMBER'), "WHATSAPP_PHONE_NUMBER not configured"
    
    client = WhatsAppWebClient()
    await client.initialize()
    
    # Test authentication (phone retrieved from environment)
    result = await client.authenticate()
    assert result['status'] in ['authenticated', 'already_authenticated']

async def test_group_creation():
    """Test family group creation"""
    # Requires authenticated session
    # Returns invite link for agent to use
    pass
```

### 7.2 Demo Rehearsal Testing

```python
async def test_demo_flow():
    """Test complete demo flow"""
    # 1. Fresh authentication with SMS
    # 2. Group creation
    # 3. Invite link generation
    # 4. Return link for agent to send emails
    # 5. Cleanup for next demo run
    pass
```

---

## 8. Demo Integration

### 8.1 Demo Day 1 Integration

**Expected Tool Calls (Two Separate Calls)**:

**First Tool Call**: `setup_whatsapp_group`
```json
{
  "group_name": "Vetticaden Family Chat",
  "group_description": "iOS to Android family bridge - better than iMessage!",
  "family_members": [
    {"name": "Jaisy", "email": "jcvetticaden@gmail.com", "relationship": "spouse"},
    {"name": "Laila", "email": "lailarvett@gmail.com", "relationship": "child"},
    {"name": "Ethan", "email": "ethanjvett@gmail.com", "relationship": "child"},
    {"name": "Maya", "email": "mayatvett@gmail.com", "relationship": "child"}
  ]
}
```

**Expected Response**:
- Group created successfully
- Invite link returned: https://chat.whatsapp.com/BQdX7R9kT5LHV8z4...

**Second Tool Call**: `send_family_emails` (Separate Gmail tool)
```json
{
  "service": "whatsapp",
  "group_name": "Vetticaden Family Chat",
  "invite_link": "https://chat.whatsapp.com/BQdX7R9kT5LHV8z4...",
  "family_members": [
    {"name": "Jaisy", "email": "jcvetticaden@gmail.com"},
    {"name": "Laila", "email": "lailarvett@gmail.com"},
    {"name": "Ethan", "email": "ethanjvett@gmail.com"},
    {"name": "Maya", "email": "mayatvett@gmail.com"}
  ]
}
```

### 8.2 Demo Success Criteria

- ✅ **Live Authentication**: Real SMS verification on camera
- ✅ **Group Creation**: Actual WhatsApp group created
- ✅ **Invite Link Generated**: Working invite link returned
- ✅ **Clear Separation**: Group creation and email sending are distinct steps
- ✅ **Family Tracking**: Member info stored for status checking

---

## 9. Community Reusability

### 9.1 Setup Documentation

```markdown
# WhatsApp Automation Setup

## Prerequisites
- WhatsApp account with phone number
- Python 3.11+
- Claude Desktop with MCP tools

## Required Environment Variables
```bash
WHATSAPP_PHONE_NUMBER=+1234567890  # Your WhatsApp phone number
```

## Installation
1. Record your WhatsApp flow: `python record_whatsapp_flow.py`
2. Install dependencies: `uv pip install -e .`
3. Configure phone number in `.env`
4. Test authentication: `python test_whatsapp.py`

## Usage
- Tool creates group and returns invite link
- Agent handles email sending separately via Gmail tools
- Session persists for 7 days
```

### 9.2 Troubleshooting Guide

- **Phone number not configured**: Set WHATSAPP_PHONE_NUMBER environment variable
- **SMS not received**: Check phone number format (+1234567890)
- **Authentication timeout**: Retry with fresh session
- **Group creation fails**: Check WhatsApp Web interface changes
- **Invite links not working**: Regenerate invite link

---

## 10. Success Criteria

### 10.1 Technical Success
- ✅ **Environment-Based Auth**: Phone number from environment only
- ✅ **Automated Authentication**: SMS/QR code login working
- ✅ **Group Creation**: Reliable group creation and setup
- ✅ **Invite Generation**: Working invite links returned
- ✅ **Clear Separation**: Email sending handled by agent, not this tool
- ✅ **Session Persistence**: 7-day session management

### 10.2 Demo Success
- ✅ **Just-in-Time Auth Check**: Environment variable checked when needed
- ✅ **Live Authentication**: Real-time SMS verification
- ✅ **Family Group Creation**: Actual group created
- ✅ **Invite Link Returned**: Agent can use link for emails
- ✅ **Two-Step Process**: Clear separation between group and email

### 10.3 Community Success
- ✅ **Simple Configuration**: Only phone number needed
- ✅ **Easy Setup**: Clear documentation
- ✅ **Reliable Operation**: Works across different accounts
- ✅ **Maintainable**: Session management reduces setup burden

This comprehensive WhatsApp requirements document provides Claude Code with everything needed to implement a robust, demo-ready WhatsApp family group automation system that creates groups and returns invite links, with the agent orchestrating email sending through separate Gmail tools.