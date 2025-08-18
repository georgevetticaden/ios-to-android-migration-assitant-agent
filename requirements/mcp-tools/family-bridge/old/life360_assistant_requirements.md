# Life360 Setup Assistant - Detailed Requirements Document
## Cross-Platform Location Sharing Bridge for Mixed iOS/Android Families

### Project Context
This document specifies requirements for automating Life360 family circle setup assistance to replace Find My when one family member switches from iPhone to Android. Since Life360's web interface has limited automation capabilities, this solution provides intelligent hybrid automation: manual invite code generation with automated family instruction distribution and adoption tracking.

---

## 1. Project Structure & Integration

### 1.1 MCP Tool Architecture
```
mcp-tools/
├── life360-assistant/
│   ├── src/life360_assistant/
│   │   ├── __init__.py
│   │   ├── life360_assistant.py      # Main assistance logic
│   │   ├── invite_manager.py         # Invite code and link management
│   │   ├── instruction_generator.py  # Setup instruction automation
│   │   ├── adoption_tracker.py       # Family member tracking
│   │   ├── server.py                 # MCP server implementation
│   │   └── email_templates.py        # Personalized instruction emails
│   ├── test_life360.py               # Standalone testing
│   ├── pyproject.toml
│   ├── .env
│   └── README.md
```

### 1.2 Integration with Existing Tools
- **Database**: Shares DuckDB with photo-migration, whatsapp, and venmo tools
- **Gmail API**: Uses same Gmail credentials for instruction automation
- **Family Data**: Coordinated with WhatsApp and Venmo family member data
- **MCP Server**: Independent server, runs alongside other family bridge tools

---

## 2. Life360 Hybrid Automation Strategy

### 2.1 Core Limitations & Hybrid Approach

**Key Constraints**:
- Life360 web interface (app.life360.com) has very limited functionality
- Invite codes must be generated manually in mobile app
- Family circle creation requires mobile app interaction
- 2-day invite code expiration requires timing coordination

**Hybrid Solution Strategy**:
1. **Manual Code Generation**: Guide user through generating invite code in Life360 app
2. **Automated Instruction Distribution**: Send personalized setup emails to each family member
3. **Adoption Tracking**: Monitor family member responses and circle membership
4. **Expiration Management**: Handle 2-day code expiration with renewal assistance
5. **Cross-Platform Optimization**: Ensure instructions work for both iOS and Android family members

### 2.2 Demo Integration Approach
- **Day 2-3**: Guide manual invite code generation, send family instructions
- **Day 4**: Show family adoption status and location sharing success
- **Day 5**: Demonstrate working cross-platform location sharing

---

## 3. Life360 Assistant Implementation

### 3.1 Main Life360 Assistant Logic

```python
class Life360Assistant:
    """Life360 family circle setup assistance with hybrid automation"""
    
    def __init__(self, gmail_client, database):
        self.gmail_client = gmail_client
        self.db = database
        self.invite_code_expiry_hours = 48  # Life360 standard
    
    async def setup_family_circle(
        self,
        circle_name: str,
        family_members: List[Dict[str, Any]],
        user_phone: str,
        user_email: str
    ) -> Dict[str, Any]:
        """
        Setup Life360 family circle with hybrid manual/automated approach
        
        Args:
            circle_name: Name for the Life360 family circle
            family_members: List of family member info
            user_phone: User's phone number for Life360 account
            user_email: User's email for coordination
        """
        
        try:
            # Step 1: Guide user through manual invite code generation
            logger.info("Initiating Life360 setup with manual code generation guidance")
            
            code_generation_guide = self._generate_code_instructions()
            
            # Display instructions to user
            print("=" * 60)
            print("📍 Life360 Family Circle Setup")
            print("=" * 60)
            print("STEP 1: Generate Invite Code in Life360 App")
            print(code_generation_guide["instructions"])
            print("=" * 60)
            
            # Prompt for invite code
            invite_code = await self._get_invite_code_from_user()
            
            if not invite_code:
                raise Exception("Invite code required to proceed with Life360 setup")
            
            # Step 2: Validate and store invite code
            validated_code = self._validate_invite_code(invite_code)
            
            # Step 3: Create circle record in database
            circle_id = await self._create_circle_record(
                circle_name=circle_name,
                invite_code=validated_code,
                user_phone=user_phone,
                user_email=user_email
            )
            
            # Step 4: Send personalized instructions to each family member
            instruction_results = []
            for member in family_members:
                result = await self._send_member_instructions(
                    member=member,
                    circle_name=circle_name,
                    invite_code=validated_code,
                    circle_id=circle_id
                )
                instruction_results.append(result)
            
            # Step 5: Initialize adoption tracking
            await self._initialize_adoption_tracking(circle_id, family_members)
            
            return {
                "status": "setup_initiated",
                "circle_id": circle_id,
                "circle_name": circle_name,
                "invite_code": validated_code,
                "code_expires_at": self._calculate_expiry_time(),
                "family_members_contacted": len(family_members),
                "instruction_results": instruction_results,
                "setup_timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Life360 setup failed: {e}")
            raise
    
    def _generate_code_instructions(self) -> Dict[str, str]:
        """Generate step-by-step instructions for manual code generation"""
        
        instructions = """Please generate an invite code in your Life360 app:

📱 STEP-BY-STEP INSTRUCTIONS:
1. Open Life360 app on your phone
2. Tap your profile (top left corner)
3. Select "Settings" from the menu
4. Choose "Circle Management"
5. Tap "Invite Members" 
6. Your invite code will appear (format: XXX-XXX)
7. Copy the code and enter it below

💡 TIPS:
- Code expires in 2 days, so share it quickly
- Code format is usually 3 letters, dash, 3 letters (like INJ-JOQ)
- If you don't see "Circle Management", you may need to create a circle first

⏰ TIMING: This setup takes about 2 minutes in the app"""
        
        return {
            "instructions": instructions,
            "estimated_time": "2-3 minutes",
            "prerequisites": ["Life360 app installed", "Life360 account created"]
        }
    
    async def _get_invite_code_from_user(self) -> str:
        """
        Get invite code from user with validation
        For demo: Can simulate user providing code
        """
        
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                # In real implementation, this would be user input
                # For demo, we can simulate or use environment variable
                demo_code = os.getenv('LIFE360_DEMO_INVITE_CODE')
                if demo_code:
                    logger.info(f"Using demo invite code: {demo_code}")
                    return demo_code
                
                # Real user input
                invite_code = input(f"\nEnter your Life360 invite code (attempt {attempt + 1}/{max_attempts}): ").strip().upper()
                
                if self._validate_invite_code_format(invite_code):
                    return invite_code
                else:
                    print("❌ Invalid format. Code should be like 'INJ-JOQ' (3 letters, dash, 3 letters)")
                    
            except KeyboardInterrupt:
                raise Exception("Life360 setup cancelled by user")
            except Exception as e:
                logger.warning(f"Error getting invite code: {e}")
        
        raise Exception("Failed to get valid invite code after multiple attempts")
    
    def _validate_invite_code_format(self, code: str) -> bool:
        """Validate Life360 invite code format"""
        import re
        
        # Life360 codes are typically XXX-XXX format
        pattern = r'^[A-Z]{3}-[A-Z]{3}$'
        return bool(re.match(pattern, code))
    
    def _validate_invite_code(self, code: str) -> str:
        """Enhanced validation and formatting of invite code"""
        
        if not self._validate_invite_code_format(code):
            raise ValueError(f"Invalid invite code format: {code}. Expected format: XXX-XXX")
        
        # Additional validation could include:
        # - Check against known invalid codes
        # - Verify code hasn't expired
        # - Confirm code hasn't been used already
        
        logger.info(f"Validated Life360 invite code: {code}")
        return code
    
    async def _create_circle_record(
        self, 
        circle_name: str,
        invite_code: str,
        user_phone: str,
        user_email: str
    ) -> str:
        """Create circle record in database"""
        
        circle_id = f"LC-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        await self.db.execute("""
            INSERT INTO life360_circles (
                circle_id, circle_name, invite_code, creator_phone, 
                creator_email, created_at, code_expires_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            circle_id,
            circle_name,
            invite_code,
            user_phone,
            user_email,
            datetime.now().isoformat(),
            self._calculate_expiry_time(),
            'active'
        ))
        
        return circle_id
    
    def _calculate_expiry_time(self) -> str:
        """Calculate invite code expiration time (48 hours from now)"""
        expiry = datetime.now() + timedelta(hours=self.invite_code_expiry_hours)
        return expiry.isoformat()
    
    async def _send_member_instructions(
        self,
        member: Dict[str, Any],
        circle_name: str, 
        invite_code: str,
        circle_id: str
    ) -> Dict[str, Any]:
        """Send personalized Life360 instructions to family member"""
        
        try:
            # Generate personalized instructions based on relationship and device
            instructions = self._generate_member_instructions(
                member=member,
                circle_name=circle_name,
                invite_code=invite_code
            )
            
            # Send instruction email
            email_result = await self.gmail_client.send_family_setup_email(
                to_email=member["email"],
                subject=instructions["subject"],
                body=instructions["body"]
            )
            
            # Record instruction sending
            await self._record_member_instruction(
                circle_id=circle_id,
                member=member,
                email_result=email_result
            )
            
            if email_result["status"] == "sent":
                return {
                    "name": member["name"],
                    "relationship": member.get("relationship", "family"),
                    "email": member["email"],
                    "status": "instructions_sent",
                    "sent_at": datetime.now().isoformat()
                }
            else:
                return {
                    "name": member["name"],
                    "status": "instruction_failed",
                    "error": email_result.get("error", "Unknown email error")
                }
                
        except Exception as e:
            logger.error(f"Failed to send instructions to {member['name']}: {e}")
            return {
                "name": member["name"],
                "status": "instruction_failed", 
                "error": str(e)
            }
    
    def _generate_member_instructions(
        self,
        member: Dict[str, Any],
        circle_name: str,
        invite_code: str
    ) -> Dict[str, str]:
        """Generate personalized instructions based on family member profile"""
        
        name = member["name"]
        relationship = member.get("relationship", "family member")
        
        # Customize tone and urgency based on relationship
        if relationship == "spouse":
            tone = "direct"
            urgency = "This is important for family safety and coordination."
            benefits = """✅ More accurate than Find My
✅ Driving reports and safety alerts  
✅ Emergency assistance features
✅ Works perfectly across iPhone and Android"""
            
        elif relationship in ["child", "teen"]:
            tone = "casual"
            urgency = "Dad needs this for family coordination now that he's on Android."
            benefits = """✅ Parents can see you're safe
✅ Works on any phone (iPhone or Android)
✅ Better location accuracy than Find My
✅ Cool driving reports when you get your license"""
            
        else:
            tone = "friendly"
            urgency = "This helps our family stay connected across different phones."
            benefits = """✅ Cross-platform location sharing
✅ Family safety and coordination
✅ Emergency features
✅ Better than Find My for mixed device families"""
        
        # Generate setup instructions
        setup_steps = f"""**Setup Instructions:**
1. Download Life360 from your App Store
2. Create account or sign in if you have one
3. When prompted to join a circle, enter this code: **{invite_code}**
4. You'll be added to "{circle_name}" automatically

**Important:** This code expires in 2 days, so please set up soon!"""
        
        subject = f"Life360 Family Circle - {circle_name}"
        
        body = f"""Hi {name}!

{urgency}

Dad switched to Android, so we need a new family location app that works across all phones.

**Join our Life360 family circle:**
Circle Name: {circle_name}
Invite Code: **{invite_code}**

{setup_steps}

**Why Life360?**
{benefits}

**Need help?** Just text Dad or ask in our family WhatsApp group!

**Remember:** Code expires in 2 days - please join soon! ⏰

Love,
Dad 📱➡️🤖

---
*This helps keep our family connected and safe across all devices*"""
        
        return {
            "subject": subject,
            "body": body,
            "tone": tone,
            "invite_code": invite_code
        }
    
    async def _record_member_instruction(
        self,
        circle_id: str,
        member: Dict[str, Any],
        email_result: Dict[str, Any]
    ):
        """Record instruction sending in database"""
        
        await self.db.execute("""
            INSERT INTO life360_member_instructions (
                circle_id, member_name, member_email, relationship,
                instruction_sent_at, email_status, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            circle_id,
            member["name"],
            member["email"],
            member.get("relationship", "family"),
            datetime.now().isoformat(),
            email_result["status"],
            json.dumps(email_result)
        ))
    
    async def _initialize_adoption_tracking(
        self,
        circle_id: str, 
        family_members: List[Dict[str, Any]]
    ):
        """Initialize adoption tracking for all family members"""
        
        for member in family_members:
            await self.db.execute("""
                INSERT INTO life360_adoption_tracking (
                    circle_id, member_name, member_email, 
                    status, last_checked, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                circle_id,
                member["name"],
                member["email"],
                "instructions_sent",
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
```

### 3.2 Adoption Tracking & Status Management

```python
class Life360AdoptionTracker:
    """Track family member adoption of Life360 circle"""
    
    def __init__(self, gmail_client, database):
        self.gmail_client = gmail_client
        self.db = database
    
    async def check_circle_adoption_status(
        self,
        circle_id: str
    ) -> Dict[str, Any]:
        """
        Check adoption status of Life360 circle members
        Combines email monitoring with manual status updates
        """
        
        try:
            # Get circle info
            circle_info = await self.db.fetch_one("""
                SELECT * FROM life360_circles WHERE circle_id = ?
            """, (circle_id,))
            
            if not circle_info:
                raise Exception(f"Circle {circle_id} not found")
            
            # Check code expiration
            code_expired = self._is_code_expired(circle_info["code_expires_at"])
            
            # Get all family members for this circle
            members = await self.db.fetch_all("""
                SELECT * FROM life360_adoption_tracking 
                WHERE circle_id = ? 
                ORDER BY member_name
            """, (circle_id,))
            
            adoption_results = []
            
            for member in members:
                # Check for manual status updates
                manual_status = await self._get_manual_status_update(
                    circle_id, member["member_name"]
                )
                
                # Check email responses
                email_responses = await self._check_email_responses(
                    member["member_email"]
                )
                
                # Determine overall adoption status
                adoption_status = self._determine_member_adoption_status(
                    member, manual_status, email_responses, code_expired
                )
                
                adoption_results.append(adoption_status)
            
            return {
                "circle_id": circle_id,
                "circle_name": circle_info["circle_name"],
                "invite_code": circle_info["invite_code"],
                "code_expired": code_expired,
                "code_expires_at": circle_info["code_expires_at"],
                "total_members": len(members),
                "adoption_results": adoption_results,
                "checked_at": datetime.now().isoformat(),
                "summary": self._generate_adoption_summary(adoption_results, code_expired)
            }
            
        except Exception as e:
            logger.error(f"Circle adoption check failed: {e}")
            raise
    
    def _is_code_expired(self, expires_at: str) -> bool:
        """Check if invite code has expired"""
        expiry_time = datetime.fromisoformat(expires_at)
        return datetime.now() > expiry_time
    
    async def _get_manual_status_update(
        self, 
        circle_id: str, 
        member_name: str
    ) -> Dict[str, Any]:
        """Get manual status updates for demo/parent reporting"""
        
        status_update = await self.db.fetch_one("""
            SELECT * FROM life360_status_updates 
            WHERE circle_id = ? AND member_name = ?
            ORDER BY updated_at DESC 
            LIMIT 1
        """, (circle_id, member_name))
        
        if status_update:
            return {
                "has_manual_update": True,
                "status": status_update["status"],
                "updated_at": status_update["updated_at"],
                "notes": status_update["notes"]
            }
        
        return {"has_manual_update": False}
    
    async def _check_email_responses(self, member_email: str) -> List[Dict]:
        """Check for email responses from family member"""
        
        try:
            # Search for Life360-related email responses
            response_emails = await self.gmail_client.search_emails(
                query=f"from:{member_email} subject:life360 OR subject:location OR subject:circle",
                days_back=7
            )
            
            responses = []
            for email in response_emails:
                parsed_response = self._parse_member_response(email)
                responses.append(parsed_response)
            
            return responses
            
        except Exception as e:
            logger.warning(f"Could not check email responses for {member_email}: {e}")
            return []
    
    def _determine_member_adoption_status(
        self,
        member: Dict,
        manual_status: Dict,
        email_responses: List[Dict],
        code_expired: bool
    ) -> Dict[str, Any]:
        """Determine overall adoption status for family member"""
        
        # Priority: Manual status > Email responses > Time-based estimation
        if manual_status["has_manual_update"]:
            return {
                "name": member["member_name"],
                "email": member["member_email"],
                "status": manual_status["status"],
                "method": "manual_update",
                "details": manual_status["notes"],
                "last_updated": manual_status["updated_at"],
                "code_expired": code_expired
            }
        
        elif email_responses:
            latest_response = email_responses[-1]
            return {
                "name": member["member_name"],
                "email": member["member_email"],
                "status": latest_response["interpreted_status"],
                "method": "email_response",
                "details": latest_response["summary"],
                "last_updated": latest_response["received_at"],
                "code_expired": code_expired
            }
        
        else:
            # Time and expiration-based estimation
            hours_since_instruction = (datetime.now() - datetime.fromisoformat(member["created_at"])).total_seconds() / 3600
            
            if code_expired:
                estimated_status = "code_expired"
                details = "Invite code expired - needs new code"
            elif hours_since_instruction <= 24:
                estimated_status = "instructions_sent"
                details = "Recently sent instructions"
            elif hours_since_instruction <= 48:
                estimated_status = "in_progress"
                details = "Likely reviewing setup instructions"
            else:
                estimated_status = "follow_up_needed"
                details = "May need reminder or new invite code"
            
            return {
                "name": member["member_name"],
                "email": member["member_email"],
                "status": estimated_status,
                "method": "time_estimation",
                "details": details,
                "hours_since_instruction": round(hours_since_instruction, 1),
                "code_expired": code_expired
            }
    
    def _generate_adoption_summary(
        self, 
        results: List[Dict],
        code_expired: bool
    ) -> Dict[str, Any]:
        """Generate summary of adoption across all family members"""
        
        status_counts = {}
        for result in results:
            status = result["status"]
            status_counts[status] = status_counts.get(status, 0) + 1
        
        successful_joins = len([r for r in results if r["status"] in ["joined_circle", "active_member"]])
        
        needs_action = []
        if code_expired:
            needs_action.extend([r["name"] for r in results if r["status"] not in ["joined_circle", "active_member"]])
        
        needs_follow_up = [r["name"] for r in results if r["status"] == "follow_up_needed"]
        
        return {
            "total_members": len(results),
            "successful_joins": successful_joins,
            "success_rate": (successful_joins / len(results)) * 100 if results else 0,
            "status_breakdown": status_counts,
            "code_expired": code_expired,
            "needs_new_code": needs_action,
            "needs_follow_up": needs_follow_up,
            "circle_health": "excellent" if successful_joins == len(results) else "needs_attention"
        }
    
    async def record_manual_status_update(
        self,
        circle_id: str,
        member_name: str,
        status: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Record manual status update for family member
        
        Status options: 'joined_circle', 'active_member', 'needs_help', 'not_interested'
        """
        
        await self.db.execute("""
            INSERT INTO life360_status_updates (
                circle_id, member_name, status, notes, updated_at
            ) VALUES (?, ?, ?, ?, ?)
        """, (circle_id, member_name, status, notes, datetime.now().isoformat()))
        
        # Update adoption tracking table
        await self.db.execute("""
            UPDATE life360_adoption_tracking 
            SET status = ?, last_checked = ?
            WHERE circle_id = ? AND member_name = ?
        """, (status, datetime.now().isoformat(), circle_id, member_name))
        
        return {
            "circle_id": circle_id,
            "member_name": member_name,
            "status": status,
            "notes": notes,
            "updated_at": datetime.now().isoformat()
        }
    
    async def renew_expired_code(
        self,
        circle_id: str,
        new_invite_code: str
    ) -> Dict[str, Any]:
        """Handle invite code renewal when original expires"""
        
        try:
            # Update circle with new code
            await self.db.execute("""
                UPDATE life360_circles 
                SET invite_code = ?, code_expires_at = ?, updated_at = ?
                WHERE circle_id = ?
            """, (
                new_invite_code,
                (datetime.now() + timedelta(hours=48)).isoformat(),
                datetime.now().isoformat(),
                circle_id
            ))
            
            # Get members who haven't joined yet
            pending_members = await self.db.fetch_all("""
                SELECT * FROM life360_adoption_tracking 
                WHERE circle_id = ? AND status NOT IN ('joined_circle', 'active_member')
            """, (circle_id,))
            
            return {
                "circle_id": circle_id,
                "new_invite_code": new_invite_code,
                "new_expiry": (datetime.now() + timedelta(hours=48)).isoformat(),
                "pending_members": len(pending_members),
                "members_to_notify": [m["member_name"] for m in pending_members]
            }
            
        except Exception as e:
            logger.error(f"Code renewal failed: {e}")
            raise
```

---

## 4. MCP Server Integration

### 4.1 Life360 Assistant MCP Tools

```python
#!/usr/bin/env python3.11
"""
Life360 Setup Assistant MCP Server
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

from .life360_assistant import Life360Assistant
from .adoption_tracker import Life360AdoptionTracker

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("life360-assistant")
life360_assistant = None
adoption_tracker = None

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Life360 setup assistance tools"""
    return [
        types.Tool(
            name="setup_life360_circle",
            description="Setup Life360 family circle with manual invite code + automated instructions",
            inputSchema={
                "type": "object",
                "properties": {
                    "circle_name": {
                        "type": "string",
                        "default": "Family Circle",
                        "description": "Name for the Life360 family circle"
                    },
                    "user_phone": {
                        "type": "string",
                        "description": "User's phone number for Life360 account"
                    },
                    "user_email": {
                        "type": "string",
                        "description": "User's email for coordination"
                    },
                    "family_members": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "relationship": {"type": "string"}
                            },
                            "required": ["name", "email"]
                        },
                        "description": "Family members to invite to Life360 circle"
                    }
                },
                "required": ["user_phone", "user_email", "family_members"]
            }
        ),
        types.Tool(
            name="check_life360_adoption",
            description="Check Life360 circle adoption status and member activity",
            inputSchema={
                "type": "object",
                "properties": {
                    "circle_id": {
                        "type": "string",
                        "description": "Life360 circle ID to check"
                    }
                },
                "required": ["circle_id"]
            }
        ),
        types.Tool(
            name="record_life360_member_status", 
            description="Record manual status update for Life360 member (for demo/parent reporting)",
            inputSchema={
                "type": "object",
                "properties": {
                    "circle_id": {"type": "string"},
                    "member_name": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["joined_circle", "active_member", "needs_help", "not_interested"]
                    },
                    "notes": {"type": "string", "optional": True}
                },
                "required": ["circle_id", "member_name", "status"]
            }
        ),
        types.Tool(
            name="renew_life360_code",
            description="Handle Life360 invite code renewal when code expires",
            inputSchema={
                "type": "object",
                "properties": {
                    "circle_id": {"type": "string"},
                    "new_invite_code": {"type": "string"}
                },
                "required": ["circle_id", "new_invite_code"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle Life360 setup assistance tool calls"""
    global life360_assistant, adoption_tracker
    
    try:
        # Initialize services
        if life360_assistant is None:
            gmail_creds_path = os.getenv('GMAIL_CREDENTIALS_PATH')
            if not gmail_creds_path:
                return [types.TextContent(
                    type="text",
                    text="❌ Gmail credentials not configured. Please set GMAIL_CREDENTIALS_PATH."
                )]
            
            from ..photo_migration.gmail_integration import FamilyGmailClient
            from ..shared.database import SharedDatabase
            
            gmail_client = FamilyGmailClient(gmail_creds_path)
            await gmail_client.initialize()
            
            database = SharedDatabase()
            await database.initialize()
            
            life360_assistant = Life360Assistant(gmail_client, database)
            adoption_tracker = Life360AdoptionTracker(gmail_client, database)
        
        if name == "setup_life360_circle":
            circle_name = arguments.get("circle_name", "Family Circle")
            user_phone = arguments["user_phone"]
            user_email = arguments["user_email"]
            family_members = arguments["family_members"]
            
            # Execute Life360 setup (includes manual code generation guidance)
            result = await life360_assistant.setup_family_circle(
                circle_name=circle_name,
                family_members=family_members,
                user_phone=user_phone,
                user_email=user_email
            )
            
            # Format response
            response = f"""📍 Life360 Family Circle Setup Complete!

**Circle Details:**
- Name: {result['circle_name']}
- Circle ID: {result['circle_id']}
- Invite Code: **{result['invite_code']}**
- Code Expires: {result['code_expires_at']} (2 days)

**Family Instructions Sent:**"""
            
            for instruction_result in result["instruction_results"]:
                if instruction_result["status"] == "instructions_sent":
                    response += f"\n✅ {instruction_result['name']} ({instruction_result.get('relationship', 'family')}) - Setup email sent"
                else:
                    response += f"\n❌ {instruction_result['name']} - {instruction_result.get('error', 'Failed')}"
            
            response += f"""

**Next Steps:**
1. Family members download Life360 app
2. They use invite code: **{result['invite_code']}**
3. They'll be added to your circle automatically
4. Track adoption with check_life360_adoption

**Important:** ⏰ Invite code expires in 2 days!

Your cross-platform location sharing bridge is ready! 📲✨"""
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "check_life360_adoption":
            circle_id = arguments["circle_id"]
            
            adoption_status = await adoption_tracker.check_circle_adoption_status(circle_id)
            
            response = f"""📊 Life360 Circle Status: {adoption_status['circle_name']}

**Circle Info:**
- Circle ID: {adoption_status['circle_id']}
- Invite Code: {adoption_status['invite_code']}
- Code Status: {'❌ EXPIRED' if adoption_status['code_expired'] else '✅ Active'}
- Code Expires: {adoption_status['code_expires_at']}

**Member Adoption:**"""
            
            for member in adoption_status["adoption_results"]:
                status_emoji = {
                    "joined_circle": "✅",
                    "active_member": "🎉",
                    "instructions_sent": "📧",
                    "in_progress": "⏳",
                    "needs_help": "❓",
                    "follow_up_needed": "⚠️",
                    "code_expired": "❌",
                    "not_interested": "😐"
                }.get(member["status"], "📄")
                
                response += f"\n{status_emoji} {member['name']}: {member['status'].replace('_', ' ').title()}"
                if member.get("details"):
                    response += f" - {member['details']}"
            
            response += f"""

**Summary:**
- Success Rate: {adoption_status['summary']['success_rate']:.1f}%
- Active Members: {adoption_status['summary']['successful_joins']}/{adoption_status['total_members']}
- Circle Health: {adoption_status['summary']['circle_health'].replace('_', ' ').title()}"""
            
            if adoption_status['code_expired'] and adoption_status['summary']['needs_new_code']:
                response += f"""

⚠️ **ACTION NEEDED: Code Expired**
Members need new invite code: {', '.join(adoption_status['summary']['needs_new_code'])}
Use renew_life360_code to generate new code and re-send instructions."""
            
            elif adoption_status['summary']['needs_follow_up']:
                response += f"""

💡 **Suggested Follow-up:**
Send reminders to: {', '.join(adoption_status['summary']['needs_follow_up'])}"""
            
            response += f"\n\n*Last checked: {adoption_status['checked_at']}*"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "record_life360_member_status":
            circle_id = arguments["circle_id"]
            member_name = arguments["member_name"]
            status = arguments["status"]
            notes = arguments.get("notes", "")
            
            update_result = await adoption_tracker.record_manual_status_update(
                circle_id=circle_id,
                member_name=member_name,
                status=status,
                notes=notes
            )
            
            status_messages = {
                "joined_circle": f"🎉 {member_name} joined the Life360 circle!",
                "active_member": f"✅ {member_name} is actively using Life360!",
                "needs_help": f"❓ {member_name} needs assistance with Life360 setup",
                "not_interested": f"😐 {member_name} is not interested in Life360"
            }
            
            response = status_messages.get(status, f"📝 Status updated for {member_name}")
            
            if notes:
                response += f"\n\n**Notes:** {notes}"
            
            response += f"\n\n*Updated: {update_result['updated_at']}*"
            
            return [types.TextContent(type="text", text=response)]
        
        elif name == "renew_life360_code":
            circle_id = arguments["circle_id"]
            new_invite_code = arguments["new_invite_code"]
            
            renewal_result = await adoption_tracker.renew_expired_code(
                circle_id=circle_id,
                new_invite_code=new_invite_code
            )
            
            response = f"""🔄 Life360 Invite Code Renewed!

**Updated Circle:**
- Circle ID: {renewal_result['circle_id']}
- New Code: **{renewal_result['new_invite_code']}**
- Expires: {renewal_result['new_expiry']} (2 days)

**Members to Notify:** {renewal_result['pending_members']} pending
- {', '.join(renewal_result['members_to_notify'])}

**Next Steps:**
1. Share new code with pending members
2. Send follow-up instructions if needed
3. Monitor adoption with check_life360_adoption

Your Life360 circle is ready for new members! 📍"""
            
            return [types.TextContent(type="text", text=response)]
        
        else:
            return [types.TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        logger.error(f"Life360 tool execution error: {e}")
        return [types.TextContent(type="text", text=f"❌ Error: {str(e)}")]

async def main():
    """Main entry point"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Life360 Setup Assistant MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="life360-assistant",
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

## 5. Database Schema Extension

### 5.1 Life360 Tables (Extends Shared DuckDB)

```sql
-- Add to existing shared database

-- Life360 family circles
CREATE TABLE life360_circles (
    id INTEGER PRIMARY KEY,
    circle_id VARCHAR UNIQUE,
    circle_name VARCHAR,
    invite_code VARCHAR,
    creator_phone VARCHAR,
    creator_email VARCHAR,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    code_expires_at TIMESTAMP,
    status VARCHAR DEFAULT 'active' -- 'active', 'expired', 'archived'
);

-- Family member instructions tracking
CREATE TABLE life360_member_instructions (
    id INTEGER PRIMARY KEY,
    circle_id VARCHAR,
    member_name VARCHAR,
    member_email VARCHAR,
    relationship VARCHAR, -- 'spouse', 'child', 'teen', 'parent'
    instruction_sent_at TIMESTAMP,
    email_status VARCHAR,
    metadata JSON,
    FOREIGN KEY (circle_id) REFERENCES life360_circles(circle_id)
);

-- Adoption tracking
CREATE TABLE life360_adoption_tracking (
    id INTEGER PRIMARY KEY,
    circle_id VARCHAR,
    member_name VARCHAR,
    member_email VARCHAR,
    status VARCHAR, -- 'instructions_sent', 'in_progress', 'joined_circle', 'active_member'
    last_checked TIMESTAMP,
    created_at TIMESTAMP,
    FOREIGN KEY (circle_id) REFERENCES life360_circles(circle_id)
);

-- Manual status updates (for demo and parent reporting)
CREATE TABLE life360_status_updates (
    id INTEGER PRIMARY KEY,
    circle_id VARCHAR,
    member_name VARCHAR,
    status VARCHAR, -- 'joined_circle', 'active_member', 'needs_help', 'not_interested'
    notes TEXT,
    updated_at TIMESTAMP,
    updated_by VARCHAR DEFAULT 'parent',
    FOREIGN KEY (circle_id) REFERENCES life360_circles(circle_id)
);
```

---

## 6. Demo Integration Specification

### 6.1 Demo Day 2-3 Flow

**Day 2-3: Life360 Setup**

**User Input**: "Let's replace Find My with Life360 for family location sharing."

**Tool Call**: `setup_life360_circle`

**Parameters**:
```json
{
    "circle_name": "Vetticaden Family",
    "user_phone": "+1234567890",
    "user_email": "dad@example.com",
    "family_members": [
        {"name": "Sarah", "email": "sarah@example.com", "relationship": "spouse"},
        {"name": "Ethan", "email": "ethan@example.com", "relationship": "child"},
        {"name": "Emma", "email": "emma@example.com", "relationship": "child"},
        {"name": "Alex", "email": "alex@example.com", "relationship": "child"}
    ]
}
```

**Demo Experience**:
1. Agent displays step-by-step instructions for generating invite code
2. User generates code in Life360 app (manual step - shown on screen)
3. User provides code to agent (e.g., "INJ-JOQ")
4. Agent sends personalized instructions to all 4 family members
5. Agent confirms setup and provides tracking ID

**Day 4: Adoption Status Check**

**User Input**: "How's my family adopting Life360?"

**Tool Call**: `check_life360_adoption`

**Demo Response** (using manual status updates):
- Sarah (spouse): "Joined circle - 'Actually more accurate than Find My'" ✅
- Ethan (16): "Active member - loving the driving reports" 🎉
- Emma (14): "Successfully joined circle" ✅
- Alex (11): "Completed setup with help" ✅

### 6.2 Manual Status Updates for Demo

```python
# Pre-demo setup for realistic family responses
await adoption_tracker.record_manual_status_update(
    circle_id="LC-20250817-143000",
    member_name="Sarah",
    status="active_member",
    notes="Actually more accurate than Find My - love the features"
)

await adoption_tracker.record_manual_status_update(
    circle_id="LC-20250817-143000", 
    member_name="Ethan",
    status="active_member",
    notes="The driving reports are actually cool!"
)

await adoption_tracker.record_manual_status_update(
    circle_id="LC-20250817-143000",
    member_name="Emma", 
    status="joined_circle",
    notes="Setup completed successfully"
)

await adoption_tracker.record_manual_status_update(
    circle_id="LC-20250817-143000",
    member_name="Alex",
    status="joined_circle", 
    notes="Needed help but working great now"
)
```

---

## 7. Error Handling & Edge Cases

### 7.1 Invite Code Expiration Management

```python
async def handle_code_expiration(self, circle_id: str) -> Dict[str, Any]:
    """Handle invite code expiration gracefully"""
    
    try:
        # Check which members still need to join
        pending_members = await self.db.fetch_all("""
            SELECT * FROM life360_adoption_tracking 
            WHERE circle_id = ? AND status NOT IN ('joined_circle', 'active_member')
        """, (circle_id,))
        
        if not pending_members:
            return {
                "action": "no_action_needed",
                "message": "All family members have already joined"
            }
        
        # Guide user through generating new code
        print("⚠️ Life360 invite code has expired!")
        print("Please generate a new code in your Life360 app:")
        print("1. Open Life360 app")
        print("2. Go to Settings > Circle Management")  
        print("3. Generate new invite code")
        
        new_code = await self._get_invite_code_from_user()
        
        # Update database and notify pending members
        renewal_result = await self.adoption_tracker.renew_expired_code(
            circle_id=circle_id,
            new_invite_code=new_code
        )
        
        # Send updated instructions to pending members
        for member in pending_members:
            await self._send_code_renewal_email(member, new_code)
        
        return {
            "action": "code_renewed",
            "new_code": new_code,
            "members_notified": len(pending_members),
            "renewal_result": renewal_result
        }
        
    except Exception as e:
        logger.error(f"Code expiration handling failed: {e}")
        return {
            "action": "manual_intervention_needed",
            "error": str(e),
            "recommendation": "Generate new code manually and use renew_life360_code tool"
        }
```

### 7.2 Family Member Communication Issues

```python
async def handle_member_non_adoption(
    self,
    circle_id: str,
    non_adopting_members: List[str]
) -> Dict[str, Any]:
    """Handle family members who haven't adopted Life360"""
    
    follow_up_strategies = []
    
    for member_name in non_adopting_members:
        # Get member info
        member_info = await self.db.fetch_one("""
            SELECT * FROM life360_member_instructions 
            WHERE circle_id = ? AND member_name = ?
        """, (circle_id, member_name))
        
        if member_info:
            relationship = member_info["relationship"]
            
            # Customize follow-up strategy based on relationship
            if relationship == "spouse":
                strategy = {
                    "approach": "direct_conversation",
                    "message": "Have a direct conversation about family safety needs",
                    "tone": "understanding but firm"
                }
            elif relationship in ["child", "teen"]:
                strategy = {
                    "approach": "gamification",
                    "message": "Emphasize cool features like driving reports",
                    "tone": "casual and benefits-focused"
                }
            else:
                strategy = {
                    "approach": "gentle_reminder",
                    "message": "Send simple reminder with clear benefits",
                    "tone": "helpful and patient"
                }
            
            follow_up_strategies.append({
                "member": member_name,
                "relationship": relationship,
                "strategy": strategy
            })
    
    return {
        "members_needing_follow_up": len(non_adopting_members),
        "strategies": follow_up_strategies,
        "recommended_action": "personal_conversation_then_reminder_email"
    }
```

---

## 8. Testing & Quality Assurance

### 8.1 Manual Code Generation Testing

```python
# test_life360.py
async def test_invite_code_validation():
    """Test invite code format validation"""
    
    assistant = Life360Assistant(mock_gmail, mock_db)
    
    # Valid codes
    assert assistant._validate_invite_code_format("INJ-JOQ") == True
    assert assistant._validate_invite_code_format("ABC-XYZ") == True
    
    # Invalid codes
    assert assistant._validate_invite_code_format("INJ-JOQQ") == False  # Too long
    assert assistant._validate_invite_code_format("IN-JOQ") == False   # Too short
    assert assistant._validate_invite_code_format("123-456") == False  # Numbers
    assert assistant._validate_invite_code_format("INJ_JOQ") == False  # Wrong separator

async def test_code_expiration_logic():
    """Test invite code expiration detection"""
    
    tracker = Life360AdoptionTracker(mock_gmail, mock_db)
    
    # Expired code (3 days ago)
    expired_time = (datetime.now() - timedelta(days=3)).isoformat()
    assert tracker._is_code_expired(expired_time) == True
    
    # Valid code (1 day ago)
    valid_time = (datetime.now() - timedelta(days=1)).isoformat()
    assert tracker._is_code_expired(valid_time) == False
```

### 8.2 Email Instruction Testing

```python
async def test_instruction_personalization():
    """Test personalized instruction generation"""
    
    assistant = Life360Assistant(mock_gmail, mock_db)
    
    # Test spouse instructions
    spouse_instructions = assistant._generate_member_instructions(
        member={"name": "Sarah", "relationship": "spouse"},
        circle_name="Family Circle",
        invite_code="INJ-JOQ"
    )
    
    assert "important for family safety" in spouse_instructions["body"]
    assert spouse_instructions["tone"] == "direct"
    
    # Test teen instructions
    teen_instructions = assistant._generate_member_instructions(
        member={"name": "Ethan", "relationship": "teen"},
        circle_name="Family Circle", 
        invite_code="INJ-JOQ"
    )
    
    assert "driving reports" in teen_instructions["body"]
    assert teen_instructions["tone"] == "casual"
```

---

## 9. Success Criteria

### 9.1 Technical Success
- ✅ **Hybrid Automation**: Manual code generation + automated instruction distribution
- ✅ **Code Management**: Proper validation, expiration tracking, renewal support
- ✅ **Family Personalization**: Relationship-based instruction customization
- ✅ **Adoption Tracking**: Monitor family member responses and circle membership
- ✅ **Expiration Handling**: Graceful code renewal and member re-notification

### 9.2 Demo Success
- ✅ **Manual Step Integration**: Smooth guidance through code generation
- ✅ **Family Response Simulation**: Show realistic family adoption patterns
- ✅ **Cross-Platform Success**: Demonstrate iOS/Android location sharing
- ✅ **Find My Replacement**: Show successful transition from Apple ecosystem

### 9.3 Community Success
- ✅ **Real Family Usage**: Families successfully adopt Life360 circles
- ✅ **Clear Instructions**: Non-technical family members can follow setup
- ✅ **Adoption Support**: Tools help families overcome setup obstacles
- ✅ **Long-term Value**: Families prefer Life360 over Find My for mixed ecosystems

### 9.4 Real-World Validation
- ✅ **Actual Code Generation**: Tool handles real Life360 invite codes
- ✅ **Family Coordination**: Successful multi-member circle creation
- ✅ **Location Sharing**: Working cross-platform location tracking
- ✅ **Safety Features**: Families utilize driving reports and emergency features

This comprehensive Life360 Setup Assistant requirements document provides everything needed to implement a sophisticated hybrid automation system that acknowledges the limitations of Life360's web interface while maximizing automation where possible, creating compelling demo moments that showcase real family coordination and cross-platform location sharing success.