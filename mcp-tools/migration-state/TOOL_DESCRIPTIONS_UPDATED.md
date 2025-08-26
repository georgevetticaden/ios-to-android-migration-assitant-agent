# Migration State Tools - Updated Descriptions Summary

## Overview

Updated all 16 tool descriptions in `migration-state/server.py` to align with the 7-day iOS to Android migration workflow and provide clear guidance on when and how the iOS2Android Agent should use each tool.

## Key Updates

### 1. Day-Specific Guidance
- **DAY 1 TOOLS**: `initialize_migration`, `add_family_member`, `start_photo_transfer`
- **DAYS 4-7 TOOLS**: `update_photo_progress` (when photos become visible)
- **DAY 5 TOOL**: `activate_venmo_card` (when teen cards arrive)
- **DAY 7 TOOL**: `generate_migration_report` (completion celebration)
- **DAILY TOOLS**: `get_daily_summary`, `get_migration_overview`

### 2. Workflow Integration
- Tools now reference the complete workflow context (7-day timeline)
- Clear expectations about when things happen (photos visible Day 4, cards arrive Day 5)
- Proper sequencing guidance (e.g., use after web-automation tools)

### 3. Parameter Clarity
- Required vs optional parameters clearly explained
- Context for when to provide optional parameters
- Expected data sources (e.g., from iCloud checks, mobile-mcp verification)

### 4. State Management Guidance
- Which tools update database state vs query-only
- Status progression flows (not_started → invited → installed → configured)
- Relationship between tools and database tables

## Tool Categories by Workflow Phase

### Setup Phase (Day 1)
```
initialize_migration    - Start new migration with iCloud photo counts
add_family_member      - Add family members for app adoption tracking  
start_photo_transfer   - Record Apple transfer initiation
```

### Progress Tracking (Days 1-7)
```
update_migration_progress   - Advance through migration phases
update_family_member_apps   - Track app adoption status changes
update_photo_progress      - Update photo transfer metrics (Day 4+)
```

### Daily Monitoring 
```
get_daily_summary      - Day-specific status with proper expectations
get_migration_overview - Comprehensive current status anytime
get_migration_status   - Detailed migration state information
```

### Completion Phase (Days 5-7)
```
activate_venmo_card       - Record teen card activation (Day 5)
generate_migration_report - Final celebration report (Day 7)
```

### Support Tools (Anytime)
```
get_statistics        - Data for React visualizations
log_migration_event   - Record significant events
create_action_item    - Track follow-up tasks
get_pending_items     - Check what needs attention
mark_item_complete    - Mark tasks as done
```

## Key Workflow Alignment Features

### Timeline Accuracy
- Photos not visible until Day 3-4 (reflected in get_daily_summary)
- Venmo cards arrive Day 5 (activate_venmo_card timing)
- Completion confirmation Day 7 (generate_migration_report)

### Family Coordination
- App adoption tracking through 4 statuses: not_started → invited → installed → configured
- Email invitation coordination (create_action_item + mobile-mcp execution)
- Cross-platform group management (WhatsApp, Google Maps, Venmo)

### Agent Guidance
- Clear "WHEN TO USE" guidance for each tool
- References to companion tools (web-automation, mobile-mcp)
- Expected data flow between tools

### React Visualization Support
- All tools return JSON optimized for visualization
- Progress percentages, status indicators, completion metrics
- Celebration-ready data structure for Day 7

## Technical Validation

✅ All syntax validated
✅ 16 tools maintain backward compatibility  
✅ Parameter schemas unchanged (no breaking changes)
✅ Enhanced descriptions provide clear agent guidance
✅ Workflow timeline accurately reflected
✅ Database operations properly categorized

## Next Steps

These updated descriptions will help the iOS2Android Agent:
1. Choose the right tools at the right time in the 7-day flow
2. Understand realistic expectations (photos visible Day 4, not Day 1)
3. Coordinate effectively with web-automation and mobile-mcp
4. Create compelling React visualizations from the returned data
5. Maintain family relationships while managing the migration

The descriptions now serve as both API documentation and workflow orchestration guidance for the agent.