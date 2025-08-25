# Claude Code Instructions V2 - Implementation Guide

## Context

You are implementing updates to support a 7-day iOS to Android migration demo. The system already has working photo migration via web-automation (formerly photo-migration) and three MCP servers are operational in Claude Desktop. These updates focus on implementing a simplified database schema and additional MCP tools to support the complete demo flow.

## Current State (DO NOT MODIFY)

### What's Already Working
- **web-automation MCP server** (photo migration via iCloud)
  - Location: `mcp-tools/web-automation/`
  - Status: PRODUCTION READY - Transfer TRF-20250820-180056 running
  - Tools: 5 tools for photo workflow
  
- **mobile-mcp** (Android control via natural language)
  - Location: `mcp-tools/mobile-mcp/`
  - Status: Integrated and tested with Galaxy Z Fold 7
  - External project - DO NOT MODIFY
  
- **migration-state server** (basic 6 tools)
  - Location: `mcp-tools/migration-state/`
  - Status: Basic wrapper operational
  - Needs: 10 additional tools

### Infrastructure Status
- ✅ DuckDB database operational
- ✅ Session persistence working
- ✅ Centralized logging to `logs/`
- ✅ Claude Desktop configuration complete
- ✅ All three MCP servers visible in Claude Desktop

## What You're Implementing

### 1. New Simplified Database Schema (7 tables)
Replacing the current over-engineered 4-schema design with a single unified schema

### 2. Ten Additional MCP Tools
Adding to migration-state server to support demo flow

### 3. Demo Day Progression Logic
Supporting the 7-day migration timeline

### 4. Family App Coordination
WhatsApp, Google Maps, and Venmo setup tracking

## Requirements Documents Reading Order

### Phase 1: Understand the Foundation

#### 1. Database Foundation
**Read**: `requirements/mcp-tools/state-management/database-design-v2.md`

Key points to understand:
- Single `migration` schema replacing 4 current schemas
- 7 focused tables vs current 17 tables
- Every table maps to demo requirements
- Email-based family coordination (not phone numbers)
- Progressive data population through demo days

Critical tables:
- `migration_status` - Core tracking
- `family_members` - Requires emails for invitations
- `photo_transfer` - Photos visible Day 4
- `app_setup` - WhatsApp, Maps, Venmo only
- `family_app_adoption` - Individual status tracking
- `daily_progress` - Demo snapshots
- `venmo_setup` - Teen card activation

#### 2. MCP Tools Specification
**Read**: `requirements/mcp-tools/state-management/migration-state-tools-v2.md`

Key points to understand:
- 10 new tools to ADD (not replace) to existing 6
- Each tool returns raw JSON for Claude visualization
- Tools map to specific demo script moments
- Day-aware logic (photos don't show until Day 4)

Critical tools:
- `initialize_migration` - Starts after iCloud check
- `add_family_member` - Stores emails, triggers teen logic
- `get_daily_summary` - Different returns per day
- `generate_migration_report` - Final celebration

### Phase 2: Understand the Demo Flow

#### 3. Family Apps Requirements
**Read**: `requirements/mcp-tools/family-bridge/family-ecosystem-requirements-v2.md`

Key points to understand:
- NO app installation automation - just email coordination
- Natural language commands only to mobile-mcp
- Progressive adoption over multiple days
- Only 3 apps: WhatsApp, Google Maps, Venmo

Important patterns:
- Try to add member → detect if no app → send email → check later
- Email template for all invitations
- Status progression: not_started → invited → installed → configured

#### 4. Demo Flow Specification
**Read**: `requirements/mcp-tools/system-integration/demo-flow-technical-spec-v2.md`

Key points to understand:
- Exact conversation flow for each day
- Tool execution sequences with inputs/outputs
- Database state after each operation
- Validation points for each day

Day highlights:
- Day 1: Setup everything, 2/4 have WhatsApp
- Day 3: Add remaining WhatsApp members
- Day 4: Photos suddenly visible at 28%
- Day 5: Venmo cards arrive and activate
- Day 7: Completion with celebration

#### 5. Integration Patterns
**Read**: `requirements/mcp-tools/system-integration/integration-spec-v2.md`

Key points to understand:
- Three MCP servers with distinct responsibilities
- No direct tool-to-tool communication
- Claude orchestrates everything
- Natural language principles for mobile-mcp

Critical patterns:
- Sequential: WhatsApp creation flow
- Parallel: Photos transfer while apps setup
- State-driven: Read state → decide → act

## Your Implementation Tasks

### Phase 1: Analysis and Planning

Before writing any code:

1. **Map current schema to new schema**
   - Identify what tables can be dropped
   - Determine if any data needs preserving
   - Plan migration approach

2. **Analyze tool additions**
   - Review existing 6 tools in migration-state
   - Understand how 10 new tools integrate
   - Identify shared code patterns

3. **Create implementation plan** including:
   - Specific files to modify
   - Implementation sequence
   - Testing approach for each component
   - Risk assessment

### Phase 2: Database Implementation

```python
# Location: shared/database/schemas/migration_schema_v2.sql

# Steps:
1. Backup existing database (if needed)
2. Create new schema file with complete SQL from database-design-v2.md
3. Execute schema creation
4. Verify all constraints and indexes created
5. Test with sample inserts for each table
```

### Phase 3: MCP Tools Implementation

```python
# Location: mcp-tools/migration-state/server.py

# Add to existing imports
from datetime import datetime, timedelta
import json

# Add to handle_list_tools() - append to existing list
new_tools = [
    # ... 10 new tool definitions from migration-state-tools-v2.md
]

# Implement each tool handler
async def handle_initialize_migration(arguments: dict) -> str:
    # Implementation from requirements
    pass

# ... implement remaining 9 tools
```

### Phase 4: Integration Testing

#### Test Day 1 Flow
```python
# Initialize migration with photo counts
result = await initialize_migration({
    "user_name": "George",
    "photo_count": 58460,
    "video_count": 2418,
    "storage_gb": 383
})
assert "migration_id" in result

# Add family members
for member in ["Jaisy", "Laila", "Ethan", "Maya"]:
    result = await add_family_member({
        "name": member,
        "email": f"{member.lower()}.vetticaden@gmail.com"
    })
    assert result["status"] == "added"

# Start photo transfer
result = await start_photo_transfer()
assert result["status"] == "transfer_initiated"
```

#### Test Day Progression
- Day 3: Update WhatsApp adoption
- Day 4: Update photo progress to 28%
- Day 5: Activate Venmo cards
- Day 7: Generate final report

### Phase 5: Demo Validation

Run complete 7-day demo flow:

1. **Day 1**: Initialize, add family, start transfer
2. **Day 3**: Complete WhatsApp group
3. **Day 4**: Verify photos visible at 28%
4. **Day 5**: Activate teen cards
5. **Day 7**: Confirm completion, generate report

## Key Implementation Constraints

### DO NOT Modify
- ❌ web-automation server (photo migration working)
- ❌ mobile-mcp (external project)
- ❌ Existing photo transfer data
- ❌ Current session persistence logic

### DO Preserve
- ✅ Existing migration_db.py functionality
- ✅ Current logging configuration
- ✅ Environment variable handling
- ✅ Claude Desktop configuration

### DO Use
- ✅ Natural language for all mobile-mcp commands
- ✅ Raw JSON returns from all tools
- ✅ Email addresses (not phone numbers) for family
- ✅ Progressive status updates through demo days

## Database Migration Strategy

Since this is a new implementation with no production data to preserve:

```sql
-- Safe approach
1. Check if photo transfer is running
   SELECT * FROM photo_migration.transfers WHERE status = 'in_progress';
   
2. If yes, note the transfer_id and progress

3. Drop old schemas and create new
   -- Run complete SQL from database-design-v2.md
   
4. If transfer was running, manually insert record
   INSERT INTO migration.photo_transfer (...) VALUES (...);
```

## Testing Data

Use these consistent values across all tests:

### Family Members
```python
family = [
    {"name": "Jaisy", "email": "jaisy.vetticaden@gmail.com", "role": "spouse"},
    {"name": "Laila", "email": "laila.vetticaden@gmail.com", "role": "child", "age": 17},
    {"name": "Ethan", "email": "ethan.vetticaden@gmail.com", "role": "child", "age": 15},
    {"name": "Maya", "email": "maya.vetticaden@gmail.com", "role": "child", "age": 11}
]
```

### Photo Data
```python
photos = {
    "count": 58460,
    "videos": 2418,
    "storage_gb": 383,
    "day_4_progress": 28,  # 16,387 photos
    "day_4_size_gb": 107
}
```

### App Adoption Timeline
- Day 1: Laila and Maya have WhatsApp
- Day 3: Jaisy and Ethan get WhatsApp
- Day 5: Venmo cards arrive for teens
- Day 7: All apps fully configured

## Success Criteria

### Database Success
- ✅ New schema created without errors
- ✅ All 7 tables with proper constraints
- ✅ Foreign keys enforce integrity
- ✅ Views return correct summaries

### MCP Tools Success
- ✅ All 10 new tools added to server
- ✅ Each tool returns valid JSON
- ✅ Tools handle missing data gracefully
- ✅ Day-specific logic works correctly

### Demo Flow Success
- ✅ Day 1: Migration initialized with family
- ✅ Day 3: WhatsApp group complete
- ✅ Day 4: Photos visible at 28%
- ✅ Day 5: Venmo cards activated
- ✅ Day 7: Celebration report generated

### Integration Success
- ✅ All three MCP servers work together
- ✅ State remains consistent
- ✅ Natural language commands execute
- ✅ No manual intervention needed

## Common Pitfalls to Avoid

### Database Pitfalls
- ❌ Don't use phone numbers - use emails
- ❌ Don't create cross-schema foreign keys
- ❌ Don't forget teen account logic (age 13-17)
- ❌ Don't show photo progress before Day 4

### Tool Implementation Pitfalls
- ❌ Don't throw exceptions - return error JSON
- ❌ Don't assume data exists - check first
- ❌ Don't format output - return raw JSON
- ❌ Don't make decisions - Claude orchestrates

### Integration Pitfalls
- ❌ Don't have tools call other tools
- ❌ Don't store state in mobile-mcp
- ❌ Don't modify web-automation
- ❌ Don't use coordinates for mobile commands

## Error Handling Patterns

### Tool Error Returns
```python
# Good error handling
try:
    # ... database operation
    return json.dumps({"status": "success", "data": result})
except Exception as e:
    return json.dumps({"status": "error", "message": str(e)})
```

### Missing Data Handling
```python
# Check before using
migration = db.get_active_migration()
if not migration:
    return json.dumps({"status": "no_active_migration"})
```

### Day-Aware Logic
```python
# Photos don't show until Day 4
if day_number < 4:
    photo_progress = 0
    message = "Transfer running, not visible yet"
else:
    photo_progress = actual_progress
    message = f"{photo_progress}% complete"
```

## Questions to Answer Before Starting

1. **Is photo transfer TRF-20250820-180056 still running?**
   - If yes, plan to preserve this data
   - If no, start fresh

2. **Are there any custom modifications to migration_db.py?**
   - Review changes to preserve functionality
   - Ensure compatibility with new schema

3. **What's the current state of migration-state server.py?**
   - Identify where to add new tools
   - Check for any custom patterns to follow

4. **Are all file paths correct for the environment?**
   - Verify database path
   - Check log directory
   - Confirm import paths

## Final Checklist Before Implementation

- [ ] Read all 5 V2 requirements documents
- [ ] Understand the 7-day demo flow
- [ ] Identify files to modify
- [ ] Plan database migration approach
- [ ] Prepare test data
- [ ] Set up testing environment
- [ ] Backup current database
- [ ] Document any assumptions

## Support Resources

If unclear about requirements:
1. Check `demo-script-v7-aligned.md` in project knowledge
2. Review `mcp-tools-v7.py` for tool implementation details
3. Reference `migration-schema-v7.sql` for exact SQL
4. Ask for clarification before implementing

Remember: The goal is to support a compelling 7-day demo showing complete iOS to Android migration with family coordination, not to build a production system with every edge case handled.

---

*This guide provides everything needed to implement the V2 requirements. Focus on demo success over perfection.*