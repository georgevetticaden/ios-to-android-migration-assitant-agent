# WhatsApp Automation Requirements Document - Final Version
## Browser-Based Group Creation with Contact Search and Member Addition

### Executive Summary
This document specifies requirements for automating WhatsApp Web group creation using Playwright browser automation. The implementation uses the existing `record_flow.py` tool from photo-migration module to capture the automation workflow, then creates groups by searching for family members by name and adding those found in contacts, while generating invite links for those not found.

**Core Capability**: Create WhatsApp groups, search and add members by name, generate invite links for non-contacts.

---

## 1. Project Context & Architecture

### 1.1 Problem Statement
When migrating from iPhone to Android in a mixed-ecosystem family, iMessage groups become unusable. WhatsApp provides cross-platform messaging but requires manual group setup. This tool automates group creation, intelligently adding family members who are already WhatsApp contacts and generating invite links for others.

### 1.2 Existing Tools to Leverage
```
photo-migration/
├── record_flow.py              # ✅ COPY THIS - Recording tool pattern
├── src/photo_migration/
│   └── icloud_client.py       # ✅ REFERENCE - Session management pattern
```

### 1.3 Architecture Position
```
family-bridge/
└── src/family_bridge/
    ├── whatsapp/
    │   ├── record_whatsapp_flow.py  # Adapted from record_flow.py
    │   ├── browser_automation.py    # Core automation
    │   └── group_manager.py          # Group creation logic
    ├── services/                     # Email services (separate)
    └── server.py                     # MCP server
```

### 1.4 Scope
**IN SCOPE**:
- Recording WhatsApp Web workflow using existing tool pattern
- Phone number authentication with SMS verification
- Group creation with custom name and description
- **Member search by name** (e.g., "Maya Vetticaden", "Wife")
- **Automatic member addition** for contacts found
- **Invite link generation** for members not in contacts
- Session persistence (14-day WhatsApp Web sessions)

**OUT OF SCOPE**:
- Email sending (handled by family_services component)
- Phone number collection (only names and emails collected)
- WhatsApp Business API integration

---

## 2. MANDATORY: Recording Tool First

### 2.1 Step 1: Adapt Existing Recording Tool

**Claude Code Instructions - MUST DO FIRST**:

```python
# COPY FROM: photo-migration/record_flow.py
# CREATE: family-bridge/src/family_bridge/whatsapp/record_whatsapp_flow.py

class WhatsAppFlowRecorder:
    """
    Adapted from photo-migration's record_flow.py
    Records WhatsApp Web workflow to capture current selectors
    
    MUST BE RUN BEFORE ANY IMPLEMENTATION
    """
    
    async def record_complete_flow(self):
        """
        Record these steps manually:
        
        1. Navigate to web.whatsapp.com
        2. Authenticate (phone number method)
        3. Enter SMS verification code
        4. Click new chat button
        5. Click new group option
        6. IMPORTANT: Record member search field
        7. Search for a contact by name
        8. Select contact from results
        9. Click next/arrow button
        10. Enter group name
        11. Enter group description
        12. Create group
        13. Open group settings
        14. Generate invite link
        
        This captures all selectors needed for automation
        """
        
        print("=" * 80)
        print("WHATSAPP WEB FLOW RECORDER")
        print("Based on photo-migration/record_flow.py pattern")
        print("=" * 80)
        print("\nCRITICAL STEPS TO RECORD:")
        print("- Member search field selector")
        print("- How search results appear")
        print("- Contact selection mechanism")
        print("- All navigation elements")
        print("=" * 80)
```

### 2.2 Recording Output Structure

```
family-bridge/
└── recorded_flow/
    ├── whatsapp_flow.json       # Complete flow with all steps
    ├── selectors.json           # Extracted selectors
    │   └── Including:
    │       - member_search_field
    │       - search_results_container
    │       - contact_item_selector
    │       - no_results_indicator
    └── screenshots/
        ├── step_006_member_search.png
        ├── step_007_search_results.png
        └── step_008_contact_selected.png
```

### 2.3 Critical Selectors to Capture

```python
# These MUST be captured by the recording tool
CRITICAL_SELECTORS = {
    "member_search_field": "TBD - from recording",  # "Search name or number" input
    "search_results_container": "TBD - from recording",
    "contact_in_results": "TBD - from recording",  # How contacts appear in search
    "no_results_message": "TBD - from recording",  # When contact not found
    "selected_member_chip": "TBD - from recording",  # Selected member indicator
    "next_button": "TBD - from recording",  # Arrow to proceed
}
```

---

## 3. Core Implementation (After Recording)

### 3.1 WhatsApp Web Client

```python
class WhatsAppWebClient:
    """
    WhatsApp Web automation with contact search capability
    """
    
    def __init__(self, session_dir: Optional[str] = None):
        # Load selectors from recording - NEVER HARDCODE
        self.SELECTORS = self._load_recorded_selectors()
        
        # Session management (from icloud_client.py pattern)
        if session_dir:
            self.session_dir = Path(session_dir)
        else:
            session_dir = os.getenv('WHATSAPP_SESSION_DIR', '~/.whatsapp_session')
            self.session_dir = Path(os.path.expanduser(session_dir))
        
        self.session_dir.mkdir(exist_ok=True)
        self.session_file = self.session_dir / "whatsapp_state.json"
        self.SESSION_VALIDITY_DAYS = 14
    
    def _load_recorded_selectors(self) -> Dict[str, str]:
        """Load selectors from recording - CRITICAL"""
        try:
            with open('recorded_flow/selectors.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise Exception(
                "❌ No recorded flow found!\n"
                "Run record_whatsapp_flow.py FIRST to capture selectors"
            )
```

### 3.2 Authentication Flow

```python
async def authenticate(self, force_fresh_login: bool = False) -> Dict[str, Any]:
    """
    Authenticate with WhatsApp Web
    Phone number from WHATSAPP_PHONE_NUMBER environment variable
    """
    
    phone_number = os.getenv('WHATSAPP_PHONE_NUMBER')
    if not phone_number:
        return {
            "status": "error",
            "message": "Please configure WHATSAPP_PHONE_NUMBER in environment"
        }
    
    # Check existing session
    if not force_fresh_login and self.is_session_valid():
        await self._restore_session()
        
        # Verify session still works
        main_panel = await self.page.query_selector(
            self.SELECTORS["main_panel"]
        )
        if main_panel:
            return {"status": "already_authenticated"}
    
    # Fresh authentication
    return await self._perform_authentication(phone_number)
```

### 3.3 Group Creation with Member Search

```python
async def create_family_group(
    self,
    group_name: str,
    group_description: str = "",
    family_members: List[Dict] = None
) -> Dict[str, Any]:
    """
    Create WhatsApp group with intelligent member addition
    
    Args:
        group_name: "Vetticaden Family Chat"
        group_description: "iOS to Android family bridge"
        family_members: [
            {"name": "Wife", "email": "..."},  # Might be in contacts
            {"name": "Maya Vetticaden", "email": "..."},  # Might not be
            {"name": "Ethan Vetticaden", "email": "..."},
            {"name": "Laila", "email": "..."}
        ]
    
    Returns:
        {
            "group_name": "Vetticaden Family Chat",
            "members_added_directly": ["Wife", "Laila"],
            "members_need_invite": ["Maya Vetticaden", "Ethan Vetticaden"],
            "invite_link": "https://chat.whatsapp.com/...",
            "total_members": 4,
            "successfully_added": 2
        }
    """
    
    # Navigate to new group creation
    await self.page.click(self.SELECTORS["new_chat_button"])
    await asyncio.sleep(1000)
    await self.page.click(self.SELECTORS["new_group_option"])
    await asyncio.sleep(1000)
    
    # Member selection phase
    members_added = []
    members_not_found = []
    
    if family_members:
        logger.info(f"Attempting to add {len(family_members)} family members")
        
        # Wait for search field
        search_field = await self.page.wait_for_selector(
            self.SELECTORS["member_search_field"],
            timeout=5000
        )
        
        for member in family_members:
            member_name = member["name"]
            logger.info(f"Searching for: {member_name}")
            
            # Clear and search for member
            await search_field.click()
            await search_field.fill("")  # Clear first
            await asyncio.sleep(500)
            await search_field.type(member_name, delay=100)  # Type naturally
            await asyncio.sleep(1500)  # Wait for search results
            
            # Check if contact found in results
            contact_found = await self._check_contact_in_results(member_name)
            
            if contact_found:
                # Click to select contact
                await contact_found.click()
                members_added.append(member_name)
                logger.info(f"✅ Added {member_name} to group")
                
                # Take screenshot for debugging
                await self.page.screenshot(
                    path=f"screenshots/member_added_{member_name}.png"
                )
            else:
                members_not_found.append(member)
                logger.info(f"❌ {member_name} not found in contacts")
            
            # Clear search for next member
            await search_field.click()
            await search_field.fill("")
            await asyncio.sleep(500)
    
    # Proceed to group details (with or without members)
    logger.info(f"Proceeding with {len(members_added)} members added")
    await self.page.click(self.SELECTORS["next_button"])
    await asyncio.sleep(1000)
    
    # Enter group name
    name_input = await self.page.wait_for_selector(
        self.SELECTORS["group_name_input"],
        timeout=5000
    )
    await name_input.fill(group_name)
    
    # Enter description if provided
    if group_description and "group_description_input" in self.SELECTORS:
        desc_input = await self.page.query_selector(
            self.SELECTORS["group_description_input"]
        )
        if desc_input:
            await desc_input.fill(group_description)
    
    # Create group
    await self.page.click(self.SELECTORS["create_group_button"])
    await asyncio.sleep(2000)
    
    # Generate invite link for members not found
    invite_link = await self._generate_invite_link()
    
    # Take final screenshot
    await self.page.screenshot(
        path=f"screenshots/group_created_{group_name}.png"
    )
    
    return {
        "status": "success",
        "group_name": group_name,
        "group_description": group_description,
        "members_added_directly": members_added,
        "members_need_invite": [m["name"] for m in members_not_found],
        "invite_link": invite_link,
        "total_members_requested": len(family_members) if family_members else 0,
        "successfully_added": len(members_added),
        "need_email_invite": len(members_not_found),
        "created_at": datetime.now().isoformat()
    }

async def _check_contact_in_results(self, member_name: str) -> Optional[ElementHandle]:
    """
    Check if contact appears in search results
    Uses selectors from recording
    """
    
    # Wait briefly for results to load
    await asyncio.sleep(1000)
    
    # Look for contact in results using recorded selectors
    # The recorder should capture how contacts appear
    contact_selectors = [
        f'text="{member_name}"',  # Exact match
        f'*text*="{member_name}"',  # Partial match
        f'{self.SELECTORS.get("contact_in_results", "")}:has-text("{member_name}")'
    ]
    
    for selector in contact_selectors:
        if selector:  # Skip empty selectors
            contact = await self.page.query_selector(selector)
            if contact:
                # Verify it's actually a selectable contact
                is_visible = await contact.is_visible()
                if is_visible:
                    return contact
    
    # Check for "no results" indicator
    no_results = await self.page.query_selector(
        self.SELECTORS.get("no_results_message", 'text="No results"')
    )
    if no_results:
        logger.info(f"WhatsApp shows no results for {member_name}")
    
    return None

async def _generate_invite_link(self) -> str:
    """Generate group invite link"""
    
    # Open group info
    await self.page.click(self.SELECTORS["group_header"])
    await asyncio.sleep(1000)
    
    # Find and click invite link option
    invite_option = await self.page.wait_for_selector(
        self.SELECTORS["invite_link_option"],
        timeout=5000
    )
    await invite_option.click()
    
    # Copy link
    copy_button = await self.page.wait_for_selector(
        self.SELECTORS["copy_link_button"],
        timeout=5000
    )
    await copy_button.click()
    
    # Get link from clipboard (or extract from page)
    # Implementation depends on browser permissions
    invite_link = "https://chat.whatsapp.com/[GENERATED]"
    
    return invite_link
```

---

## 4. MCP Tool Interface

### 4.1 Tool Definition

```python
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="setup_whatsapp_group",
            description="Create WhatsApp group and add family members by name search",
            inputSchema={
                "type": "object",
                "properties": {
                    "group_name": {
                        "type": "string",
                        "description": "Name for the family group"
                    },
                    "group_description": {
                        "type": "string",
                        "description": "Optional group description",
                        "default": "iOS to Android family bridge"
                    },
                    "family_members": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Contact name to search (e.g., 'Wife', 'Maya Vetticaden')"
                                },
                                "email": {
                                    "type": "string",
                                    "description": "Email for sending invite if not in contacts"
                                },
                                "relationship": {
                                    "type": "string",
                                    "enum": ["spouse", "child", "parent", "sibling", "other"]
                                }
                            },
                            "required": ["name", "email"]
                        },
                        "description": "Family members to add (will search by name)"
                    }
                },
                "required": ["group_name", "family_members"]
            }
        )
    ]
```

### 4.2 Tool Response Handler

```python
@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict) -> list[types.TextContent]:
    if name == "setup_whatsapp_group":
        # Verify recording exists
        if not Path("recorded_flow/selectors.json").exists():
            return [types.TextContent(
                type="text",
                text="❌ Recording not found! Run record_whatsapp_flow.py first."
            )]
        
        # Check environment
        if not os.getenv('WHATSAPP_PHONE_NUMBER'):
            return [types.TextContent(
                type="text",
                text="❌ Please configure WHATSAPP_PHONE_NUMBER in environment variables."
            )]
        
        # Create group with member search
        result = await whatsapp.create_family_group(
            group_name=arguments["group_name"],
            group_description=arguments.get("group_description", ""),
            family_members=arguments.get("family_members", [])
        )
        
        # Format response based on results
        if result["status"] == "success":
            response = f"""✅ WhatsApp Family Group Created!

📱 **Group**: '{result['group_name']}'
📝 **Description**: {result['group_description']}

👥 **Members Added Directly** ({result['successfully_added']}):"""
            
            for member in result["members_added_directly"]:
                response += f"\n  ✅ {member} - Found in contacts and added"
            
            if result["members_need_invite"]:
                response += f"\n\n📧 **Need Email Invites** ({result['need_email_invite']}):"
                for member in result["members_need_invite"]:
                    response += f"\n  📨 {member} - Not in contacts, will send invite link"
            
            response += f"""

🔗 **Invite Link**: {result['invite_link']}

Next step: Email service will send personalized invitations to members not found in contacts."""
            
            return [types.TextContent(type="text", text=response)]
        else:
            return [types.TextContent(
                type="text",
                text=f"❌ Group creation failed: {result.get('error', 'Unknown error')}"
            )]
```

---

## 5. Implementation Phases

### Phase 1: Recording Tool Setup (Hour 1) - MANDATORY
1. Copy `record_flow.py` from photo-migration
2. Adapt for WhatsApp Web workflow
3. **Run recording with focus on member search**
4. Verify these are captured:
   - Member search field
   - Search results appearance
   - Contact selection mechanism
5. Generate selectors.json

### Phase 2: Core Automation (Hours 2-3)
1. Load selectors from recording
2. Implement session management (from icloud_client.py)
3. Basic navigation using recorded selectors
4. Screenshot capabilities

### Phase 3: Authentication (Hours 3-4)
1. Phone number authentication flow
2. SMS verification handling
3. Session persistence (14-day)
4. Session validation

### Phase 4: Group Creation with Search (Hours 5-7)
1. **Member search implementation**
2. **Contact detection in results**
3. **Mixed addition handling**
4. Group name/description
5. Invite link generation

### Phase 5: MCP Integration (Hours 7-8)
1. Tool definition with member array
2. Response formatting
3. Error handling
4. Testing with real contacts

---

## 6. Testing Requirements

### 6.1 Recording Verification

```python
async def test_recording_complete():
    """Ensure all critical selectors captured"""
    selectors = load_recorded_selectors()
    
    # Must have member search selectors
    assert "member_search_field" in selectors
    assert "contact_in_results" in selectors
    assert "no_results_message" in selectors
    assert "next_button" in selectors
```

### 6.2 Member Search Testing

```python
async def test_member_search_scenarios():
    """Test different search outcomes"""
    
    # Test 1: Contact found and added
    result = await search_and_add_member("Wife")
    assert result["found"] == True
    
    # Test 2: Contact not found
    result = await search_and_add_member("Maya Vetticaden")
    assert result["found"] == False
    
    # Test 3: Partial name match
    result = await search_and_add_member("Ethan")
    # Depends on contacts
```

### 6.3 Integration Testing

```python
async def test_mixed_group_creation():
    """Test group with some contacts found, others not"""
    
    result = await create_family_group(
        group_name="Test Family",
        family_members=[
            {"name": "Known Contact", "email": "known@test.com"},
            {"name": "Unknown Person", "email": "unknown@test.com"}
        ]
    )
    
    assert len(result["members_added_directly"]) >= 0
    assert len(result["members_need_invite"]) >= 0
    assert result["invite_link"] != ""
```

---

## 7. Environment Configuration

### 7.1 Required Variables

```bash
# WhatsApp Authentication (REQUIRED)
WHATSAPP_PHONE_NUMBER=+16147912019

# Paths
WHATSAPP_SESSION_DIR=~/.whatsapp_session
SCREENSHOT_DIR=./screenshots/whatsapp
RECORDING_DIR=./recorded_flow

# Browser Settings
WHATSAPP_HEADLESS=false  # False for initial setup
WHATSAPP_TIMEOUT=120000  # 2 minutes for SMS
```

### 7.2 Demo Data Example

```json
{
  "group_name": "Vetticaden Family Chat",
  "group_description": "iOS to Android family bridge - better than iMessage!",
  "family_members": [
    {"name": "Wife", "email": "jcvetticaden@gmail.com", "relationship": "spouse"},
    {"name": "Laila", "email": "lailarvett@gmail.com", "relationship": "child"},
    {"name": "Ethan Vetticaden", "email": "ethanjvett@gmail.com", "relationship": "child"},
    {"name": "Maya Vetticaden", "email": "mayatvett@gmail.com", "relationship": "child"}
  ]
}
```

---

## 8. Error Handling

### 8.1 Common Scenarios

```python
class MemberSearchError(Exception):
    """Contact search failed"""

class PartialGroupCreationError(Exception):
    """Group created but some members couldn't be added"""

async def handle_partial_success(result: Dict) -> Dict:
    """
    Handle case where group is created but not all members added
    This is actually a common SUCCESS scenario
    """
    
    if result["successfully_added"] < result["total_members_requested"]:
        # This is OK - we have invite links for the rest
        result["status"] = "partial_success"
        result["message"] = (
            f"Group created with {result['successfully_added']} members. "
            f"{result['need_email_invite']} members will receive email invites."
        )
    
    return result
```

### 8.2 Recovery Strategies

1. **Contact not found**: Generate invite link (normal flow)
2. **Search timeout**: Continue without that member
3. **Group creation fails**: Retry with empty group
4. **Session expired**: Clear and re-authenticate

---

## 9. Demo Integration

### 9.1 Expected Demo Flow

```
User: "Create our family WhatsApp group"

Claude: "Creating 'Vetticaden Family Chat' and searching for family members..."

[Tool executes]

Claude: "✅ WhatsApp Group Created!

Added directly (found in your contacts):
  ✅ Wife - Added to group
  ✅ Laila - Added to group

Need email invitations (not in contacts yet):
  📨 Maya Vetticaden - Will send invite link
  📨 Ethan Vetticaden - Will send invite link

I'll now send personalized emails to Maya and Ethan with the invite link."

[Email service sends invitations]
```

### 9.2 Success Metrics

- ✅ Group created with correct name
- ✅ Some members added directly (realistic)
- ✅ Invite link generated for others
- ✅ Clear communication about who was added
- ✅ Smooth handoff to email service

---

## 10. Key Design Decisions

### 10.1 Why Search by Name?
- Privacy: Don't need to collect phone numbers
- Natural: Matches how users think about contacts
- Flexible: Works with partial matches

### 10.2 Why Mixed Addition is OK?
- Realistic: Not all family members may be WhatsApp users yet
- Graceful: Invite links solve the problem
- Clear: User understands who needs invites

### 10.3 Why Recording Tool First?
- Accuracy: Current selectors, not guessed
- Maintainable: Easy to update when WhatsApp changes
- Proven: Pattern works in photo-migration

---

## 11. Community Usage Guide

### 11.1 Setup Instructions

```bash
# Step 1: Copy and adapt recording tool
cp photo-migration/record_flow.py family-bridge/src/family_bridge/whatsapp/record_whatsapp_flow.py

# Step 2: Run recording
python record_whatsapp_flow.py
# Complete all steps including member search

# Step 3: Verify recording
cat recorded_flow/selectors.json | grep member_search_field
# Should see the selector

# Step 4: Set environment
export WHATSAPP_PHONE_NUMBER=+1234567890

# Step 5: Test
python test_whatsapp.py
```

### 11.2 Troubleshooting

**"No contacts found"**:
- Normal if family members aren't WhatsApp users yet
- Invite links will be generated
- They can join after installing WhatsApp

**"Search not working"**:
- Re-run recording tool
- WhatsApp Web may have updated
- Check search field selector

**"Can't add members"**:
- Verify they're in your phone's contacts
- Ensure WhatsApp has contact permissions
- Try searching with different name formats

---

## Document Control

**Version**: 3.0.0 (Final)
**Key Features**: 
- Recording tool integration
- Member search by name
- Mixed addition handling (some direct, some via invite)
- Realistic demo flow

**Last Updated**: August 2025
**Status**: Ready for Claude Code implementation

This final version provides complete requirements for implementing WhatsApp group automation with intelligent member addition based on contact search.