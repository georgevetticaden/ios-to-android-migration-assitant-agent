# iOS2Android Migration Agent - Testing and Improvement Plan

## 📋 Overview

This document outlines the systematic testing and iterative improvement process for the iOS2Android Migration Agent instructions. The goal is to achieve consistent, successful execution of the complete 7-day migration flow as defined in `docs/demo/demo-script-complete-final.md`.

## 🎯 Objectives

1. **Primary Goal**: Achieve 5 consecutive successful full demo runs with 90%+ accuracy
2. **Timeline**: 2-week iterative testing and refinement cycle
3. **Outcome**: Production-ready agent instructions that consistently execute the migration journey

## 📁 Key Files

### Core Documents
- **Agent Instructions**: `agent/instructions/ios2android-agent-instructions-v3.md`
- **Demo Script**: `docs/demo/demo-script-complete-final.md`
- **Test Tracking**: `docs/test-runs/` (create per test)

### Reference Examples
- [Health Extractor Agent](https://github.com/georgevetticaden/multi-agent-health-insight-system/blob/main/agents/extractor-agent/config/agent-instructions.md)
- [Health Analyst Agent](https://github.com/georgevetticaden/multi-agent-health-insight-system/blob/main/agents/analyst-agent/config/agent-instructions.md)
- [PM Agent](https://github.com/georgevetticaden/3-amigo-agents/blob/main/agents/pm-agent/config/pm-agent-instructions.md)

### Anthropic Best Practices
- [Prompt Engineering Overview](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/overview)
- [Claude 4 Best Practices](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/claude-4-best-practices)
- [Be Clear and Direct](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/be-clear-and-direct)
- [Multi-shot Prompting](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/multishot-prompting)
- [Chain of Thought](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/chain-of-thought)
- [Use XML Tags](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/use-xml-tags)
- [System Prompts](https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/system-prompts)

## 🧪 Testing Framework

### Phase 1: Baseline Testing (Days 1-2)

#### Test Scenarios

##### Scenario 1.1: Complete Context
```markdown
User: "I just got a Samsung Galaxy Z Fold 7 after 18 years on iPhone. I need to migrate everything from iCloud - especially my almost half terabyte of photos going back to 2007. My wife Jaisy and our 3 kids - Laila who's 17, Ethan who's 15, and Maya who's 11 - they're all staying on iPhone. We rely heavily on iMessage, Find My, and Apple Cash. I need to replace these with cross-platform solutions - WhatsApp for messaging, Google Maps location sharing for Find My, and Venmo for payments. Let's call our WhatsApp group 'Vetticaden Family'. Can you help me migrate without disrupting my family?"
```

##### Scenario 1.2: Minimal Context
```markdown
User: "I'm switching from iPhone to Android after many years. Can you help?"
```

##### Scenario 1.3: Progressive Disclosure
```markdown
User: "I need help migrating from iPhone to Android"
Agent: [Asks for details]
User: "I've been on iPhone for 18 years, just got a Galaxy Z Fold 7"
Agent: [Asks about family]
User: "My wife and 3 kids are staying on iPhone"
[Continue progressively]
```

### Phase 2: Multi-Day Journey Testing

#### Day-by-Day Test Points

| Day | Key Test Points | Expected Behaviors | Success Metrics |
|-----|----------------|-------------------|-----------------|
| **Day 1** | - Initialize migration<br>- Check iCloud status<br>- Start transfer<br>- Create WhatsApp group<br>- Setup location sharing | - Calls tools in correct sequence<br>- Queries database for names<br>- Handles 3/4 found pattern<br>- SMS invite for Maya | - All tools called correctly<br>- No hardcoded names<br>- States updated properly |
| **Day 2** | - Check migration status<br>- Discover Maya joined<br>- Update WhatsApp status<br>- Check location adoption | - Uses get_migration_status(2)<br>- Mobile discovery for Maya<br>- Celebrates connection | - Maya added to group<br>- 2/4 location sharing |
| **Day 3** | - Complete location sharing<br>- Family ecosystem check | - All 4 sharing location<br>- Major celebration | - 100% WhatsApp<br>- 100% Location |
| **Day 4** | - Photos arrive!<br>- Major celebration<br>- Show Google Photos | - 28% progress shown<br>- React visualization<br>- Mobile photo browsing | - Enthusiasm for photos<br>- Accurate progress |
| **Day 5** | - Venmo card activation<br>- 57% progress | - Teen card activation flow<br>- Progress acceleration | - Cards activated<br>- Family 100% complete |
| **Day 6** | - Near completion<br>- 88% progress | - Building anticipation | - All services operational |
| **Day 7** | - Complete success<br>- Video email check<br>- Final celebration | - Only searches video success<br>- 100% presentation<br>- generate_migration_report() | - Complete success message<br>- No mention of missing items |

## 📊 Evaluation Criteria

### Critical Success Metrics

#### 1. Tool Usage Accuracy
- [ ] Always calls `check_icloud_status()` before mentioning photo counts
- [ ] Never hardcodes family names (always queries database)
- [ ] Follows exact Day 1 sequence: initialize → add_family → check_icloud → update → start_transfer
- [ ] Uses `get_migration_status(day_number)` for Days 2-7
- [ ] Progressive `update_migration_status()` enrichment

#### 2. Mobile Control Precision
- [ ] Uses exact patterns from instructions including coordinates
- [ ] Database query before mobile actions
- [ ] Handles found/not found scenarios
- [ ] Updates state based on actual discoveries
- [ ] Personalized SMS messages for missing members

#### 3. Conversation Quality
- [ ] Natural, empathetic language
- [ ] Celebrates at right moments
- [ ] Sets clear expectations (photos Day 4)
- [ ] Maintains confidence throughout
- [ ] Uses family names from database

#### 4. React Visualizations
- [ ] Creates after tool responses
- [ ] Uses actual data not placeholders
- [ ] Day-appropriate content
- [ ] Compelling and clear
- [ ] Consistent formatting

## 📝 Issue Tracking Template

Create a new file for each test run: `docs/test-runs/test-run-YYYY-MM-DD-N.md`

```markdown
# Test Run #[X] - [Date] - [Time]

## Test Configuration
- **Agent Instructions Version**: v3
- **Demo Script Section**: [e.g., Day 1 setup]
- **MCP Servers**: All running
- **Database**: Fresh/Existing

## Scenario
[e.g., Day 1 initial setup with complete context]

## User Input
```
[Exact user message]
```

## Expected Behavior (Per Demo Script)
1. [Expected action 1]
2. [Expected action 2]
3. [Expected response pattern]

## Actual Agent Response
```
[Complete agent response including tool calls]
```

## Tool Calls Analysis
| Expected Tool | Actual Tool | Parameters | Status |
|--------------|-------------|------------|---------|
| initialize_migration | [actual] | [params] | ✅/❌ |
| add_family_member x4 | [actual] | [params] | ✅/❌ |

## Issues Identified

### Issue 1: [Title]
- **Severity**: Critical/Major/Minor
- **Category**: Tool Usage/Language/State Management/Mobile Control
- **Description**: [What went wrong]
- **Line Reference**: [Instructions line # if applicable]
- **Root Cause**: [Why it happened]

### Issue 2: [Continue as needed]

## Proposed Fixes

### Fix for Issue 1
**Current Instruction (Line X):**
```markdown
[Current text]
```

**Proposed Change:**
```markdown
[New text]
```

**Rationale**: [Why this fixes the issue]

## Success Metrics This Run
- Tool Accuracy: [X/Y] = [%]
- Database Queries: [X/Y] = [%]
- Mobile Patterns: [X/Y] = [%]
- Celebrations Hit: [X/Y] = [%]

## Notes for Next Run
[Any observations or things to specifically test next time]
```

## 🔄 Iterative Improvement Protocol

### Step 1: Analyze Conversation Logs

#### Checklist for Each Test
- [ ] Tool call sequence matches demo script
- [ ] All parameters correct
- [ ] State updates occur after discoveries
- [ ] Language feels natural
- [ ] Celebrations at right moments
- [ ] React visualizations created
- [ ] Mobile patterns exact

### Step 2: Categorize Issues

#### Priority Levels

**🔴 P0 - Critical Failures** (Fix immediately)
- Wrong tool sequence
- Hardcoded names instead of database
- Missing required tool calls
- Incorrect mobile patterns
- Day 7 searching for photo completion

**🟡 P1 - Quality Issues** (Fix in next iteration)
- Unnatural language
- Missing celebrations
- Weak visualizations
- Poor expectation setting

**🟢 P2 - Edge Cases** (Document and handle)
- Unusual user inputs
- Partial information
- Error recovery scenarios

### Step 3: Apply Instruction Refinements

#### Refinement Techniques

##### 1. Clarity Enhancement
```markdown
# Before (Vague)
"Check family member status"

# After (Clear)
"ALWAYS query get_family_members(filter='not_in_whatsapp') BEFORE attempting to add members to WhatsApp"
```

##### 2. XML Tag Structure
```xml
<critical_sequence day="1">
  <step>1. initialize_migration(user_name, years_on_ios)</step>
  <step>2. add_family_member() for each family member</step>
  <step>3. check_icloud_status() - MANDATORY before mentioning counts</step>
  <step>4. update_migration_status() with photo data</step>
  <step>5. start_photo_transfer()</step>
</critical_sequence>
```

##### 3. Multi-shot Examples
```markdown
## Example: WhatsApp Discovery Pattern

### Input:
User: "Has Maya joined WhatsApp yet?"

### Correct Response:
1. Query: get_family_members(filter="not_in_whatsapp")
2. Returns: [{"name": "Maya", "status": "invited"}]
3. Mobile: "Search for Maya in WhatsApp"
4. Discovery: Maya found!
5. Update: update_family_member_apps("Maya", "WhatsApp", "configured")
6. Response: "Great news! Maya has joined WhatsApp. Let me add her to the family group..."
```

##### 4. Chain of Thought Sections
```markdown
<reasoning>
Before responding about photo counts:
1. Have I called check_icloud_status()? → No
2. Therefore: Call it first
3. After receiving data: Now I can mention specific numbers
</reasoning>
```

## 📅 Testing Schedule

### Week 1: Foundation Testing

| Day | Focus | Test Runs | Key Validation |
|-----|-------|-----------|----------------|
| **Mon-Tue** | Day 1 flows | 5 minimum | Tool sequences, family setup |
| **Wed-Thu** | Days 2-3 progression | 5 minimum | Family adoption patterns |
| **Fri** | Analysis & refinement | - | Update v3 instructions |

### Week 2: Complete Journey

| Day | Focus | Test Runs | Key Validation |
|-----|-------|-----------|----------------|
| **Mon-Tue** | Days 4-5 flows | 5 minimum | Photo arrival, Venmo activation |
| **Wed-Thu** | Days 6-7 completion | 5 minimum | Success presentation |
| **Fri** | Final refinements | - | Production ready |

## 📈 Progress Tracking

### Metrics Dashboard

Create `docs/test-runs/METRICS.md`:

```markdown
# Testing Metrics Dashboard

## Overall Progress
- Total Test Runs: [X]
- Successful Full Runs: [X]
- Current Success Rate: [X]%

## By Day Performance
| Day | Attempts | Successes | Rate | Common Issues |
|-----|----------|-----------|------|---------------|
| Day 1 | X | X | X% | [Issues] |
| Day 2 | X | X | X% | [Issues] |
[etc...]

## Tool Accuracy Trends
| Date | Run # | Tool Accuracy | DB Queries | Mobile Patterns |
|------|-------|--------------|------------|-----------------|
| [Date] | 1 | X% | X% | X% |

## Top Issues (Frequency)
1. [Issue] - X occurrences
2. [Issue] - X occurrences
```

## ✅ Success Criteria

### Minimum Requirements for Production

#### Consistency Metrics
- [ ] 5 consecutive successful full demo runs
- [ ] 90%+ tool call accuracy across all runs
- [ ] 100% database-driven discovery (no hardcoded names)
- [ ] Natural conversation flow maintained throughout

#### Quality Metrics
- [ ] All celebration moments hit appropriately
- [ ] React visualizations compelling and data-driven
- [ ] Family adoption progression feels natural
- [ ] User confidence maintained throughout journey

#### Technical Metrics
- [ ] Correct tool sequencing 100% of time
- [ ] Mobile patterns match tested instructions exactly
- [ ] State management accurate after every discovery
- [ ] Day 7 only searches for video success email

## 🚀 Next Immediate Actions

### 1. Environment Setup Checklist
- [ ] All MCP servers configured and running
- [ ] Database initialized with clean state
- [ ] Demo mode enabled in configs
- [ ] Claude Desktop restarted
- [ ] Test environment documented

### 2. First Test Run
- [ ] Execute Scenario 1.1 (complete context)
- [ ] Record full conversation in test-run file
- [ ] Note every deviation from expected behavior
- [ ] Screenshot any errors or issues

### 3. Analysis Protocol
- [ ] Identify top 3 issues from first run
- [ ] Categorize by priority (P0/P1/P2)
- [ ] Write specific instruction fixes
- [ ] Update v3 instructions
- [ ] Document in metrics dashboard

### 4. Iteration Cycle
- [ ] Test fixes with same scenario
- [ ] Verify improvements
- [ ] Test with variations
- [ ] Document patterns that work
- [ ] Add to "golden examples"

## 📚 Deliverables

### Per Test Iteration
1. **Test Run Log**: `docs/test-runs/test-run-YYYY-MM-DD-N.md`
2. **Updated Instructions**: `agent/instructions/ios2android-agent-instructions-v3.md`
3. **Metrics Update**: `docs/test-runs/METRICS.md`

### Final Deliverables
1. **Production Instructions**: Refined v3 with all fixes
2. **Test Documentation**: Complete test run history
3. **Patterns Library**: `docs/WORKING_PATTERNS.md`
4. **Troubleshooting Guide**: `docs/AGENT_TROUBLESHOOTING.md`

## 🔧 Optimization Strategies

### From Reference Agents

#### Health Extractor (Precision Focus)
- Add "CRITICAL" and "MANDATORY" markers
- Include exact validation steps
- Zero tolerance for specific errors (like hardcoded names)

#### Health Analyst (User Focus)  
- Emphasize making complex simple
- Clear explanations of what's happening
- Proactive next step suggestions

#### PM Agent (Structure Focus)
- Clear phase definitions with transitions
- Explicit success criteria per phase
- Multiple artifact creation (React dashboards)

## 📝 Session Handoff Notes

When continuing testing in a new Claude Code session:

1. **Review Last Session**:
   - Check `docs/test-runs/` for latest test
   - Review `METRICS.md` for current success rate
   - Note outstanding issues from last run

2. **Load Context**:
   - Current instruction version
   - Known working patterns
   - Outstanding issues to test

3. **Continue Testing**:
   - Start with next scenario in sequence
   - Reference this plan for methodology
   - Update metrics after each run

## 🎯 Definition of Done

The agent instructions are complete when:

1. **Quantitative Success**:
   - 5 consecutive successful complete migrations
   - 90%+ accuracy on all metrics
   - Zero P0 issues remaining

2. **Qualitative Success**:
   - Natural conversation throughout
   - Appropriate emotional moments
   - User feels supported and confident
   - Family connectivity maintained

3. **Technical Success**:
   - All tool patterns consistent
   - Database-driven discovery working
   - Mobile control precise
   - State management accurate

---

*This plan is a living document. Update it as patterns emerge and improvements are validated.*