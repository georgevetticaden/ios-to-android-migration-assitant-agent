# Agent Instructions v5 - Improvements Summary

## Overview
Version 5 addresses the critical issues discovered in v4 testing, particularly the migration_id bug that caused family members to "disappear" and strengthens mobile control pattern enforcement.

## Key Changes from v4 to v5

### 1. 🔴 CRITICAL: Migration ID Management (NEW)

**Problem Solved:** Family members were returning empty because the agent wasn't passing migration_id to tool calls.

**v5 Solution:**
- Elevated to **Rule #1** at the very top of instructions
- Clear visual examples of correct vs wrong usage
- Emphasized storing migration_id IMMEDIATELY after initialize_migration
- Added migration_id to EVERY tool call example throughout the document
- Created "Pattern 1: Migration ID in EVERYTHING" section

**Impact:** This fixes the root cause of the database state loss issue.

### 2. 💪 Strengthened Mobile Pattern Enforcement

**Problem:** Agent was improvising instead of following exact patterns (40% accuracy).

**v5 Solution:**
- Renamed to **Rule 4: Mobile Patterns are SCRIPTS - Execute EXACTLY**
- Added stronger language: "MANDATORY SCRIPTS that have been tested and verified"
- Emphasized "NO MODIFICATIONS ALLOWED"
- Made coordinates and pauses non-negotiable

**Example Enhancement:**
```
v4: "Click the three dots (⋮) at top"
v5: "Click coordinates: 1350, 160"  // Exact coordinates required
```

### 3. 🔍 Clearer WhatsApp Search Pattern

**Problem:** Search pattern was too vague about the iterative process.

**v5 Solution:**
Added explicit step-by-step search sequence:
```
"Click the Search field at top"
"Type 'Jaisy'"
"Wait 2 seconds for search results"
"If Jaisy appears in results, tap on her contact to select (checkmark appears)"
"Click the X to clear search field"
"Type 'Laila'"
[Continue for each member]
```

### 4. ✅ Preserved v4 Successes

**Kept from v4:**
- User confirmation points (100% success rate)
- React visualization requirements (100% success rate)
- Gmail verification after transfer
- Pacing and user readiness checks

## Test Metrics Projection

### v4 → v5 Expected Improvements:

| Metric | v3 | v4 | v5 (Expected) |
|--------|----|----|---------------|
| User Confirmations | 0% | 100% ✅ | 100% ✅ |
| React Visualizations | 0% | 100% ✅ | 100% ✅ |
| Gmail Verification | 0% | 100% ✅ | 100% ✅ |
| Mobile Pattern Accuracy | 0% | 40% ⚠️ | 90%+ ✅ |
| Database Queries | 100% | 60% ⚠️ | 100% ✅ |
| Migration ID Usage | 0% | 0% ❌ | 100% ✅ |

## Critical Rules Hierarchy

v5 establishes a clear hierarchy of critical rules:

1. **Migration ID Management** - Without this, nothing works
2. **User Confirmations** - Ensures user control
3. **React Visualizations** - Provides feedback
4. **Mobile Pattern Scripts** - Ensures accurate execution

## Common Pitfalls Section

Added explicit "NEVER" statements:
- ❌ NEVER call tools without migration_id
- ❌ NEVER skip steps in critical_mobile_sequence
- ❌ NEVER assume data without querying
- ❌ NEVER proceed without confirmation

## Implementation Notes

### For Testing v5:

1. **Verify migration_id is stored and used**
   - Check first tool call is initialize_migration
   - Verify migration_id appears in ALL subsequent calls
   - Confirm no "empty family members" issues

2. **Test mobile pattern compliance**
   - Verify exact coordinates are used
   - Check all pauses are observed
   - Confirm no improvisation occurs

3. **Validate search patterns**
   - Check iterative search with clear field between
   - Verify each name is searched individually

## Success Indicators

v5 will be successful when:
- ✅ No database state loss (family members always found)
- ✅ Mobile patterns execute exactly as written
- ✅ Agent never forgets migration_id
- ✅ All v4 improvements maintained

## Migration Path

**For agents using v4:**
1. Emphasize storing migration_id from initialize_migration
2. Update all tool calls to include migration_id parameter
3. Treat mobile sequences as exact scripts, not suggestions
4. Continue with v4's successful patterns

**For new agents:**
- Start directly with v5 instructions
- Focus on Rule #1 (Migration ID) as foundation
- Practice exact mobile sequence execution

---

*v5 represents the culmination of iterative testing and refinement, addressing both technical (migration_id) and execution (mobile patterns) issues while preserving v4's UX improvements.*