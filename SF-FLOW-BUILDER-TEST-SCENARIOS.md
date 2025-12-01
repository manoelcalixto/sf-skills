# sf-flow-builder Skill Test Scenarios

**Target Org:** AgentforceScriptDemo
**Skill Version:** 1.4.0 (Optimized)
**Test Goal:** Validate all features work correctly after 48.5% optimization

---

## Test Scenario 1: Simple Screen Flow (Baseline Test)
**Complexity:** ⭐ Easy
**Estimated Time:** 5-10 minutes
**Features Tested:**
- ✅ Basic 5-phase workflow
- ✅ Template selection
- ✅ Inline validation
- ✅ Two-step deployment
- ✅ Activation prompt

### Prompt to Claude Code:
```
Create a simple screen flow for collecting feedback on a case.

Flow requirements:
- Flow Type: Screen Flow
- Name: Case_Feedback_Collection
- Purpose: Collect customer satisfaction rating and comments
- Target Org: AgentforceScriptDemo

Screens needed:
1. Welcome screen with instructions
2. Input screen: Rating (1-5 picklist), Comments (text area)
3. Confirmation screen

Keep it as Draft after deployment for testing.
```

### What to Observe:
- ✅ Asks for requirements via AskUserQuestion
- ✅ Uses TodoWrite to track phases
- ✅ Loads screen-flow-template.xml
- ✅ Validates XML structure (alphabetical ordering, locationX/Y=0)
- ✅ Runs enhanced_validator.py (or inline validation)
- ✅ Two-step deployment (validate, then deploy)
- ✅ Asks activation preference (should recommend Draft)
- ✅ Generates completion summary

### Success Criteria:
- Flow deploys successfully
- Status = Draft
- Can run from Setup → Flows
- All validation passes (score ≥ 90/110)

---

## Test Scenario 2: Record-Triggered Flow with Bulk Validation
**Complexity:** ⭐⭐ Medium
**Estimated Time:** 10-15 minutes
**Features Tested:**
- ✅ Record-triggered flow creation
- ✅ Simulation mode (bulk testing)
- ✅ DML-in-loop detection
- ✅ Fault path validation
- ✅ Transform element usage
- ✅ 6-category scoring

### Prompt to Claude Code:
```
Create a record-triggered flow that updates Account Industry field when an Opportunity is won.

Flow requirements:
- Flow Type: Record-Triggered (After Save)
- Trigger Object: Opportunity
- Trigger Condition: When StageName = "Closed Won"
- Name: RTF_Opportunity_UpdateAccountIndustry
- Action: Update related Account's Industry field to "Technology"
- Target Org: AgentforceScriptDemo

IMPORTANT: Make sure to include fault path for DML operations.
Run simulation mode to test with 200 records.
Deploy as Draft.
```

### What to Observe:
- ✅ Uses record-triggered-after-save.xml template
- ✅ Suggests using Get Records → Transform → Update Records (not loops)
- ✅ Adds fault path to Update Records element
- ✅ Runs flow_simulator.py with 200 test records
- ✅ Shows governor limit projections (SOQL, DML, CPU)
- ✅ Generates 6-category validation report with scores
- ✅ All locationX/Y = 0 (Auto-Layout)
- ✅ API version = 62.0
- ✅ No bulkSupport element (removed in API 60.0+)

### Success Criteria:
- Simulation passes (no governor limit errors)
- Validation score ≥ 85/110
- Flow deploys as Draft
- Can test by updating an Opportunity to "Closed Won"
- Fault path properly configured

---

## Test Scenario 3: Orchestration Pattern (Parent + Subflows)
**Complexity:** ⭐⭐⭐ Advanced
**Estimated Time:** 15-20 minutes
**Features Tested:**
- ✅ Orchestration pattern detection
- ✅ Parent-child flow creation
- ✅ Subflow library integration
- ✅ docs/orchestration-guide.md reference
- ✅ docs/subflow-library.md reference
- ✅ Enhanced validator (naming, security, enhanced)

### Prompt to Claude Code:
```
Create an orchestration flow for new Account onboarding that performs multiple tasks.

Flow requirements:
- Flow Type: Record-Triggered (After Save)
- Trigger Object: Account
- Trigger Condition: When Account is created (AND Type = "Customer")
- Name: RTF_Account_Onboarding_Orchestrator
- Target Org: AgentforceScriptDemo

Tasks to perform (suggest breaking into subflows):
1. Validate Account data (required fields, email format)
2. Create default Contact record with Account owner info
3. Create default Opportunity "Initial Consultation"
4. Send email alert to sales team
5. Log any errors that occur

Use standard subflows from the library where applicable.
```

### What to Observe:
- ✅ Detects complexity (multiple objects, multiple steps)
- ✅ Suggests orchestration pattern (Parent-Child or Sequential)
- ✅ References docs/orchestration-guide.md
- ✅ Offers subflows from library:
  - Sub_ValidateRecord (validation)
  - Sub_SendEmailAlert (notifications)
  - Sub_LogError (error logging)
- ✅ Asks: "Would you like me to create a parent flow and subflows?"
- ✅ Creates parent orchestrator flow
- ✅ Creates subflows (or references existing library subflows)
- ✅ All flows have proper naming conventions
- ✅ Runs naming_validator.py and security_validator.py

### Success Criteria:
- Parent flow created successfully
- Subflows created or referenced from library
- All flows use consistent naming (RTF_Account_*, Sub_*)
- Validation scores ≥ 80/110 for all flows
- Orchestration pattern documented
- Error handling with Sub_LogError

---

## Test Scenario 4: Security & Governance Testing
**Complexity:** ⭐⭐ Medium
**Estimated Time:** 10-15 minutes
**Features Tested:**
- ✅ Security & governance assessment
- ✅ docs/governance-checklist.md reference
- ✅ System mode vs User mode guidance
- ✅ Security validator
- ✅ Profile testing recommendations

### Prompt to Claude Code:
```
Create a flow that accesses sensitive salary data and updates employee records.

Flow requirements:
- Flow Type: Record-Triggered (After Save)
- Trigger Object: Employee__c (if it exists, otherwise use Contact)
- Trigger Condition: When Salary__c field changes
- Name: RTF_Employee_SalaryChangeTracking
- Action: Log salary change to Audit__c object
- Target Org: AgentforceScriptDemo

This flow will access sensitive compensation data.
```

### What to Observe:
- ✅ Detects sensitive data access
- ✅ Asks: "Has this automation been through architecture review?"
  - Options: Yes/No-non-critical/Need-guidance
- ✅ If "Need-guidance": References docs/governance-checklist.md
- ✅ Runs security_validator.py
- ✅ Discusses System mode vs User mode implications
- ✅ Warns about security review requirements
- ✅ Minimum governance score: 140/200 points for production
- ✅ Suggests profile testing (Standard User, Custom profiles)
- ✅ Recommends audit logging for compliance

### Success Criteria:
- Governance assessment performed
- Security validator runs successfully
- User mode recommended (respects FLS/CRUD)
- Documentation explains security considerations
- Testing plan includes profile testing
- Governance checklist score calculated

---

## Test Scenario 5: Error Handling & Validation Testing
**Complexity:** ⭐⭐ Medium
**Estimated Time:** 10-15 minutes
**Features Tested:**
- ✅ DML-in-loop detection (CRITICAL ERROR)
- ✅ Missing fault path detection
- ✅ Strict mode enforcement
- ✅ Auto-fix suggestions
- ✅ Error pattern references

### Prompt to Claude Code:
```
Create a flow that has intentional errors for testing validation.

Flow requirements:
- Flow Type: Record-Triggered (After Save)
- Trigger Object: Account
- Name: RTF_Account_TestValidation
- Target Org: AgentforceScriptDemo

Implement this INTENTIONALLY FLAWED logic:
1. Loop through all Contacts related to Account
2. Inside the loop, Update each Contact's Department field
3. Do NOT add fault paths to the Update element

I want to test if the validator catches these issues.
```

### What to Observe:
- ✅ Creates flow with DML-in-loop
- ✅ Validator detects CRITICAL ERROR: "DML operation inside loop"
- ✅ Blocks deployment with strict mode
- ✅ Shows error pattern: "Collect in loop → DML after loop"
- ✅ Detects missing fault path WARNING
- ✅ Offers options:
  1. Apply auto-fixes
  2. Show how to manually fix
  3. Generate corrected version
- ✅ Does NOT proceed to Phase 4 deployment

### Success Criteria:
- CRITICAL ERROR detected and blocks deployment
- Warning about missing fault path shown
- Fix pattern provided (collect → DML outside loop)
- Strict mode enforcement works
- Auto-fix or corrected version offered
- Validation score fails (< 70/110)

---

## Test Scenario 6: Documentation Generation & Completion
**Complexity:** ⭐⭐ Medium
**Estimated Time:** 10-15 minutes
**Features Tested:**
- ✅ Auto-generated documentation
- ✅ doc_generator.py usage
- ✅ Flow documentation template
- ✅ Completion summary
- ✅ Testing checklist

### Prompt to Claude Code:
```
Create a scheduled flow that cleans up old records and generates comprehensive documentation.

Flow requirements:
- Flow Type: Scheduled Flow
- Name: SF_Account_CleanupInactiveRecords
- Schedule: Daily at 2 AM
- Purpose: Delete Account records where LastActivityDate > 2 years AND Type = "Prospect"
- Target Org: AgentforceScriptDemo

After deployment, generate complete flow documentation.
```

### What to Observe:
- ✅ Uses scheduled-flow-template.xml
- ✅ Runs doc_generator.py after deployment:
  ```
  python3 ~/.claude/skills/sf-flow-builder/generators/doc_generator.py \
    force-app/main/default/flows/SF_Account_CleanupInactiveRecords.flow-meta.xml \
    docs/flows/SF_Account_CleanupInactiveRecords_documentation.md
  ```
- ✅ Documentation includes:
  - Overview (purpose, type, business context)
  - Entry/Exit criteria (schedule configuration)
  - Logic design
  - Performance metrics
  - Error handling coverage
  - Security mode
  - Testing status tracking
  - Dependencies
  - Troubleshooting guide
- ✅ References templates/flow-documentation-template.md
- ✅ Generates completion summary with:
  - Flow details, validation score, deployment info
  - Next steps (testing checklist)
  - Resource links

### Success Criteria:
- Flow deployed successfully
- Documentation file generated at docs/flows/
- Documentation follows template structure
- All sections populated
- Completion summary comprehensive
- Testing checklist for scheduled flows provided

---

## Recommended Testing Order

### Phase 1: Baseline (Start Here) ⭐
1. **Test Scenario 1**: Simple Screen Flow
   - Validates basic workflow works
   - Confirms deployment process
   - Low complexity, high confidence

### Phase 2: Core Features ⭐⭐
2. **Test Scenario 2**: Record-Triggered Flow with Bulk Validation
   - Tests simulation mode
   - Validates 6-category scoring
   - Tests Transform element usage

3. **Test Scenario 6**: Documentation Generation
   - Tests doc_generator.py
   - Validates completion summary
   - Confirms testing checklists

### Phase 3: Advanced Features ⭐⭐⭐
4. **Test Scenario 3**: Orchestration Pattern
   - Tests complexity detection
   - Validates subflow library integration
   - Tests external doc references (orchestration-guide.md, subflow-library.md)

5. **Test Scenario 4**: Security & Governance
   - Tests governance checklist
   - Validates security_validator.py
   - Tests profile testing recommendations

### Phase 4: Validation & Error Handling ⭐⭐
6. **Test Scenario 5**: Error Handling & Validation
   - Tests DML-in-loop detection
   - Validates strict mode enforcement
   - Tests auto-fix suggestions

---

## Test Tracking Checklist

- [ ] Scenario 1: Simple Screen Flow
- [ ] Scenario 2: Record-Triggered with Bulk Validation
- [ ] Scenario 3: Orchestration Pattern
- [ ] Scenario 4: Security & Governance
- [ ] Scenario 5: Error Handling & Validation
- [ ] Scenario 6: Documentation Generation

---

## After All Tests Complete

### Verify Optimization Success:
1. ✅ All features work with optimized SKILL.md (1,597 words)
2. ✅ No functionality lost from 48.5% reduction
3. ✅ External docs properly referenced
4. ✅ Validators execute correctly
5. ✅ All templates accessible
6. ✅ Two-step deployment works
7. ✅ Completion summaries comprehensive

### Report Any Issues:
- Features not working as expected
- References to docs/templates broken
- Validation scripts failing
- Missing functionality from v1.3.0

---

**Ready to start with Test Scenario 1?** 🚀
