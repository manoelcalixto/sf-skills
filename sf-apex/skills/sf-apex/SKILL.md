---
name: sf-apex
description: Generates and reviews Salesforce Apex code with 2025 best practices. 150-point scoring across 8 categories including bulkification, security, and testing. Enforces Trigger Actions Framework (TAF) pattern.
---

# sf-apex: Salesforce Apex Code Generation and Review

Expert Apex developer specializing in clean code, SOLID principles, and 2025 best practices. Generate production-ready, secure, performant, and maintainable Apex code.

## Core Responsibilities

1. **Code Generation**: Create Apex classes, triggers (TAF), tests, async jobs from requirements
2. **Code Review**: Analyze existing Apex for best practices violations with actionable fixes
3. **Validation & Scoring**: Score code against 8 categories (0-150 points)
4. **Deployment Integration**: Validate and deploy via sf-deploy skill

## Workflow (5-Phase Pattern)

### Phase 1: Requirements Gathering

Use **AskUserQuestion** to gather:
- Class type (Trigger, Service, Selector, Batch, Queueable, Test, Controller)
- Primary purpose (one sentence)
- Target object(s)
- Test requirements

**Then**:
1. Check existing code: `Glob: **/*.cls`, `Glob: **/*.trigger`
2. Check for existing Trigger Actions Framework setup: `Glob: **/*TriggerAction*.cls`
3. Create TodoWrite tasks

### Phase 2: Design & Template Selection

**Select template**:
| Class Type | Template |
|------------|----------|
| Trigger | `templates/trigger.trigger` |
| Trigger Action | `templates/trigger-action.cls` |
| Service | `templates/service.cls` |
| Selector | `templates/selector.cls` |
| Batch | `templates/batch.cls` |
| Queueable | `templates/queueable.cls` |
| Test | `templates/test-class.cls` |
| Test Data Factory | `templates/test-data-factory.cls` |
| Standard Class | `templates/apex-class.cls` |

Load via: `Read: ../../templates/[template]` (relative to SKILL.md location)

### Phase 3: Code Generation/Review

**For Generation**:
1. Create class file in `force-app/main/default/classes/`
2. Apply naming conventions (see [docs/naming-conventions.md](docs/naming-conventions.md))
3. Include ApexDoc comments
4. Create corresponding test class

**For Review**:
1. Read existing code
2. Run validation against best practices
3. Generate improvement report with specific fixes

**Run Validation**:
```
Score: XX/150 ⭐⭐⭐⭐ Rating
├─ Bulkification: XX/25
├─ Security: XX/25
├─ Testing: XX/25
├─ Architecture: XX/20
├─ Clean Code: XX/20
├─ Error Handling: XX/15
├─ Performance: XX/10
└─ Documentation: XX/10
```

### Phase 4: Deployment

**Step 1: Validation**
```
Skill(skill="sf-deploy")
Request: "Deploy classes at force-app/main/default/classes/ to [target-org] with --dry-run --test-level RunLocalTests"
```

**Step 2: Deploy** (only if validation succeeds)
```
Skill(skill="sf-deploy")
Request: "Proceed with actual deployment to [target-org]"
```

### Phase 5: Documentation & Testing Guidance

**Completion Summary**:
```
✓ Apex Code Complete: [ClassName]
  Type: [type] | API: 62.0
  Location: force-app/main/default/classes/[ClassName].cls
  Test Class: [TestClassName].cls
  Validation: PASSED (Score: XX/150)

Next Steps: Run tests, verify behavior, monitor logs
```

---

## Best Practices (Built-In Enforcement)

### Critical Requirements

**Bulkification** (25 points):
- NO SOQL/DML inside loops - collect records, operate after loop
- Use List, Set, Map for collections
- Handle 200+ records per transaction
- Test with 251+ records

**Security** (25 points):
- Use `WITH USER_MODE` for SOQL queries
- Bind variables for dynamic SOQL (`:variable`)
- Use `with sharing` by default, `inherited sharing` for utilities
- Never hardcode credentials - use Named Credentials
- Use `Security.stripInaccessible()` for FLS

**Testing** (25 points):
- 90%+ coverage (75% minimum)
- Always use Assert class (Winter '23+)
- Test positive, negative, bulk (251+), single record
- Use Test Data Factory pattern
- Use `Test.startTest()`/`Test.stopTest()` for async

**Architecture** (20 points):
- One trigger per object using Trigger Actions Framework
- Separation of concerns: Service, Domain, Selector layers
- SOLID principles compliance
- Dependency injection for testability

**Clean Code** (20 points):
- Meaningful names (no abbreviations like `tks`, `rec`)
- Self-documenting code
- Boolean clarity (no `!= false`)
- Single responsibility per method

**Error Handling** (15 points):
- Catch specific exceptions before generic
- Never empty catch blocks
- Use custom exceptions for business logic
- Log errors appropriately

**Performance** (10 points):
- Use `Limits` class to monitor
- Cache expensive operations
- Let variables go out of scope for heap
- Use async for heavy operations

**Documentation** (10 points):
- ApexDoc comments on classes/methods
- Meaningful parameter names
- Clear intent without external docs

### Scoring Thresholds

| Rating | Score |
|--------|-------|
| ⭐⭐⭐⭐⭐ Excellent | 135-150 |
| ⭐⭐⭐⭐ Very Good | 112-134 |
| ⭐⭐⭐ Good | 90-111 |
| ⭐⭐ Needs Work | 67-89 |
| ⭐ Critical Issues | <67 |

---

## Trigger Actions Framework (TAF)

### ⚠️ CRITICAL PREREQUISITES

**Before using TAF patterns, the target org MUST have:**

1. **Trigger Actions Framework Package Installed**
   - GitHub: https://github.com/mitchspano/apex-trigger-actions-framework
   - Install via: `sf package install --package 04tKZ000000gUEFYA2 --target-org [alias] --wait 10`
   - Or use unlocked package from repository

2. **Custom Metadata Type Records Created**
   - TAF triggers do NOTHING without `Trigger_Action__mdt` records!
   - Each trigger action class needs a corresponding CMT record

**If TAF is NOT installed, use the Standard Trigger Pattern instead (see below).**

---

### TAF Pattern (Requires Package)

All triggers MUST use the Trigger Actions Framework pattern:

**Trigger** (one per object):
```apex
trigger AccountTrigger on Account (
    before insert, after insert,
    before update, after update,
    before delete, after delete, after undelete
) {
    new MetadataTriggerHandler().run();
}
```

**Action Class** (one per behavior):
```apex
public class TA_Account_SetDefaults implements TriggerAction.BeforeInsert {
    public void beforeInsert(List<Account> newList) {
        for (Account acc : newList) {
            if (acc.Industry == null) {
                acc.Industry = 'Other';
            }
        }
    }
}
```

**Multi-Interface Action Class** (BeforeInsert + BeforeUpdate):
```apex
public class TA_Lead_CalculateScore implements TriggerAction.BeforeInsert, TriggerAction.BeforeUpdate {

    // Called on new record creation
    public void beforeInsert(List<Lead> newList) {
        calculateScores(newList);
    }

    // Called on record updates
    public void beforeUpdate(List<Lead> newList, List<Lead> oldList) {
        // Only recalculate if scoring fields changed
        List<Lead> leadsToScore = new List<Lead>();
        Map<Id, Lead> oldMap = new Map<Id, Lead>(oldList);

        for (Lead newLead : newList) {
            Lead oldLead = oldMap.get(newLead.Id);
            if (scoringFieldsChanged(newLead, oldLead)) {
                leadsToScore.add(newLead);
            }
        }

        if (!leadsToScore.isEmpty()) {
            calculateScores(leadsToScore);
        }
    }

    private void calculateScores(List<Lead> leads) {
        // Scoring logic here
    }

    private Boolean scoringFieldsChanged(Lead newLead, Lead oldLead) {
        return newLead.Industry != oldLead.Industry ||
               newLead.NumberOfEmployees != oldLead.NumberOfEmployees;
    }
}
```

### ⚠️ REQUIRED: Custom Metadata Type Records

**TAF triggers will NOT execute without `Trigger_Action__mdt` records!**

For each trigger action class, create a Custom Metadata record:

| Field | Value | Description |
|-------|-------|-------------|
| Label | TA Lead Calculate Score | Human-readable name |
| Trigger_Action_Name__c | TA_Lead_CalculateScore | Apex class name |
| Object__c | Lead | sObject API name |
| Context__c | Before Insert | Trigger context |
| Order__c | 1 | Execution order (lower = first) |
| Active__c | true | Enable/disable without deploy |

**Example Custom Metadata XML** (`Trigger_Action.TA_Lead_CalculateScore_BI.md-meta.xml`):
```xml
<?xml version="1.0" encoding="UTF-8"?>
<CustomMetadata xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>TA Lead Calculate Score - Before Insert</label>
    <protected>false</protected>
    <values>
        <field>Apex_Class_Name__c</field>
        <value xsi:type="xsd:string">TA_Lead_CalculateScore</value>
    </values>
    <values>
        <field>Object__c</field>
        <value xsi:type="xsd:string">Lead</value>
    </values>
    <values>
        <field>Order__c</field>
        <value xsi:type="xsd:double">1.0</value>
    </values>
    <values>
        <field>Bypass_Execution__c</field>
        <value xsi:type="xsd:boolean">false</value>
    </values>
</CustomMetadata>
```

**NOTE**: Create separate CMT records for each context (Before Insert, Before Update, etc.)

---

### Standard Trigger Pattern (No Package Required)

**Use this when TAF package is NOT installed in the target org:**

```apex
trigger LeadTrigger on Lead (before insert, before update) {

    LeadScoringService scoringService = new LeadScoringService();

    if (Trigger.isBefore) {
        if (Trigger.isInsert) {
            scoringService.calculateScores(Trigger.new);
        }
        else if (Trigger.isUpdate) {
            scoringService.recalculateIfChanged(Trigger.new, Trigger.oldMap);
        }
    }
}
```

**Pros**: No external dependencies, works in any org
**Cons**: Less maintainable for complex triggers, no declarative control

See [../../docs/trigger-actions-framework.md](../../docs/trigger-actions-framework.md) for full patterns.

---

## Async Decision Matrix

| Scenario | Use |
|----------|-----|
| Simple callout, fire-and-forget | `@future(callout=true)` |
| Complex logic, needs chaining | `Queueable` |
| Process millions of records | `Batch Apex` |
| Scheduled/recurring job | `Schedulable` |
| Post-queueable cleanup | `Queueable Finalizer` |

---

## Code Review Red Flags

| Anti-Pattern | Fix |
|--------------|-----|
| SOQL/DML in loop | Collect in loop, operate after |
| `without sharing` everywhere | Use `with sharing` by default |
| No trigger bypass flag | Add Boolean Custom Setting |
| Multiple triggers on object | Single trigger + TAF |
| SOQL without WHERE/LIMIT | Always filter and limit |
| `System.debug()` everywhere | Control via Custom Metadata |
| `isEmpty()` before DML | Remove - empty list = 0 DMLs |
| Generic Exception only | Catch specific types first |
| Hard-coded Record IDs | Query dynamically |
| No Test Data Factory | Implement Factory pattern |

---

## Modern Apex Features (API 62.0)

- **Null coalescing**: `value ?? defaultValue`
- **Safe navigation**: `record?.Field__c`
- **User mode**: `WITH USER_MODE` in SOQL
- **Assert class**: `Assert.areEqual()`, `Assert.isTrue()`

**Breaking Change (API 62.0)**: Cannot modify Set while iterating - throws `System.FinalException`

---

## Reference

**Docs**: `../../docs/` - best-practices, trigger-actions-framework, security-guide, testing-guide, naming-conventions, solid-principles, design-patterns, code-review-checklist

---

## Cross-Skill Integration

| Skill | When to Use | Example |
|-------|-------------|---------|
| sf-metadata | Discover object/fields before coding | `Skill(skill="sf-metadata")` → "Describe Invoice__c" |
| sf-data | Generate 251+ test records after deploy | `Skill(skill="sf-data")` → "Create 251 Accounts for bulk testing" |
| sf-deploy | Deploy and run tests | `Skill(skill="sf-deploy")` → "Deploy with RunLocalTests" |

## Dependencies

**All optional**: sf-deploy, sf-metadata, sf-data. Install: `/plugin install github:Jaganpro/sf-skills/[skill-name]`

## Common Exception Types Reference

When writing test classes, use these specific exception types:

| Exception Type | When to Use | Example |
|----------------|-------------|---------|
| `DmlException` | Insert/update/delete failures | `Assert.isTrue(e.getMessage().contains('FIELD_CUSTOM_VALIDATION'))` |
| `QueryException` | SOQL query failures | Malformed query, no rows for assignment |
| `NullPointerException` | Null reference access | Accessing field on null object |
| `ListException` | List operation failures | Index out of bounds |
| `MathException` | Mathematical errors | Division by zero |
| `TypeException` | Type conversion failures | Invalid type casting |
| `LimitException` | Governor limit exceeded | Too many SOQL queries, DML statements |
| `CalloutException` | HTTP callout failures | Timeout, invalid endpoint |
| `JSONException` | JSON parsing failures | Malformed JSON |
| `InvalidParameterValueException` | Invalid method parameters | Bad input values |

**Test Example:**
```apex
@IsTest
static void testShouldThrowExceptionForMissingRequiredField() {
    try {
        // Code that should throw
        insert new Account(); // Missing Name
        Assert.fail('Expected DmlException was not thrown');
    } catch (DmlException e) {
        Assert.isTrue(e.getMessage().contains('REQUIRED_FIELD_MISSING'),
            'Expected REQUIRED_FIELD_MISSING but got: ' + e.getMessage());
    }
}
```

---

## Cross-Skill Dependency Checklist

**Before deploying Apex code, verify these prerequisites:**

| Prerequisite | Check Command | Required For |
|--------------|---------------|--------------|
| TAF Package | `sf package installed list --target-org alias` | TAF trigger pattern |
| Custom Fields | `sf sobject describe --sobject Lead --target-org alias` | Field references in code |
| Permission Sets | `sf org list metadata --metadata-type PermissionSet` | FLS for custom fields |
| Trigger_Action__mdt | Check Setup → Custom Metadata Types | TAF trigger execution |

**Common Deployment Order:**
```
1. sf-metadata: Create custom fields
2. sf-metadata: Create Permission Sets
3. sf-deployment: Deploy fields + Permission Sets
4. sf-apex: Deploy Apex classes/triggers
5. sf-data: Create test data
```

---

## Notes

- **API Version**: 62.0 required
- **TAF Optional**: Prefer TAF when package is installed, use standard trigger pattern as fallback
- **Scoring**: Block deployment if score < 67

---

## License

MIT License. See [LICENSE](LICENSE) file.
Copyright (c) 2024-2025 Jag Valaiyapathy
