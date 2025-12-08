---
name: sf-metadata
description: Generates and queries Salesforce metadata including Custom Objects, Fields, Profiles, Permission Sets, Validation Rules, Record Types, and Layouts. 120-point scoring across 6 categories. Integrates with sf-apex and sf-flow-builder for on-demand object/field validation.
---

# sf-metadata: Salesforce Metadata Generation and Org Querying

Expert Salesforce administrator specializing in metadata architecture, security model design, and schema best practices. Generate production-ready metadata XML and query org structures using sf CLI v2.

## Core Responsibilities

1. **Metadata Generation**: Create Custom Objects, Fields, Profiles, Permission Sets, Validation Rules, Record Types, Page Layouts
2. **Org Querying**: Describe objects, list fields, query metadata using sf CLI v2
3. **Validation & Scoring**: Score metadata against 6 categories (0-120 points)
4. **Cross-Skill Integration**: Provide metadata discovery for sf-apex and sf-flow-builder
5. **Deployment Integration**: Deploy metadata via sf-deployment skill

## Workflow (5-Phase Pattern)

### Phase 1: Requirements Gathering

Use **AskUserQuestion** to gather:
- Operation type: **Generate** metadata OR **Query** org metadata
- If generating:
  - Metadata type (Object, Field, Profile, Permission Set, Validation Rule, Record Type, Layout)
  - Target object (for fields, validation rules, record types)
  - Specific requirements (field type, data type, relationships, picklist values)
- If querying:
  - Query type (describe object, list fields, list metadata)
  - Target org alias
  - Object name or metadata type to query

**Then**:
1. Check existing metadata: `Glob: **/*-meta.xml`, `Glob: **/objects/**/*.xml`
2. Check for sfdx-project.json to confirm Salesforce project structure
3. Create TodoWrite tasks

### Phase 2: Template Selection / Query Execution

#### For Generation

**Select template**:
| Metadata Type | Template |
|---------------|----------|
| Custom Object | `templates/objects/custom-object.xml` |
| Text Field | `templates/fields/text-field.xml` |
| Number Field | `templates/fields/number-field.xml` |
| Currency Field | `templates/fields/currency-field.xml` |
| Date Field | `templates/fields/date-field.xml` |
| Checkbox Field | `templates/fields/checkbox-field.xml` |
| Picklist Field | `templates/fields/picklist-field.xml` |
| Multi-Select Picklist | `templates/fields/multi-select-picklist.xml` |
| Lookup Field | `templates/fields/lookup-field.xml` |
| Master-Detail Field | `templates/fields/master-detail-field.xml` |
| Formula Field | `templates/fields/formula-field.xml` |
| Roll-Up Summary | `templates/fields/rollup-summary-field.xml` |
| Email Field | `templates/fields/email-field.xml` |
| Phone Field | `templates/fields/phone-field.xml` |
| URL Field | `templates/fields/url-field.xml` |
| Text Area (Long) | `templates/fields/textarea-field.xml` |
| Profile | `templates/profiles/profile.xml` |
| Permission Set | `templates/permission-sets/permission-set.xml` |
| Validation Rule | `templates/validation-rules/validation-rule.xml` |
| Record Type | `templates/record-types/record-type.xml` |
| Page Layout | `templates/layouts/page-layout.xml` |

Load via: `Read: ../../templates/[path]` (relative to SKILL.md location)

#### For Querying (sf CLI v2 Commands)

| Query Type | Command |
|------------|---------|
| Describe object | `sf sobject describe --sobject [ObjectName] --target-org [alias] --json` |
| List custom objects | `sf org list metadata --metadata-type CustomObject --target-org [alias] --json` |
| List all metadata types | `sf org list metadata-types --target-org [alias] --json` |
| List profiles | `sf org list metadata --metadata-type Profile --target-org [alias] --json` |
| List permission sets | `sf org list metadata --metadata-type PermissionSet --target-org [alias] --json` |

**Present query results** in structured format:
```
📊 Object: Account
════════════════════════════════════════

📁 Standard Fields: 45
📁 Custom Fields: 12
🔗 Relationships: 8
📝 Validation Rules: 3
📋 Record Types: 2

Custom Fields:
├── Industry_Segment__c (Picklist)
├── Annual_Revenue__c (Currency)
├── Primary_Contact__c (Lookup → Contact)
└── ...
```

### Phase 3: Generation / Validation

**For Generation**:
1. Create metadata file in appropriate directory:
   - Objects: `force-app/main/default/objects/[ObjectName__c]/[ObjectName__c].object-meta.xml`
   - Fields: `force-app/main/default/objects/[ObjectName]/fields/[FieldName__c].field-meta.xml`
   - Profiles: `force-app/main/default/profiles/[ProfileName].profile-meta.xml`
   - Permission Sets: `force-app/main/default/permissionsets/[PermSetName].permissionset-meta.xml`
   - Validation Rules: `force-app/main/default/objects/[ObjectName]/validationRules/[RuleName].validationRule-meta.xml`
   - Record Types: `force-app/main/default/objects/[ObjectName]/recordTypes/[RecordTypeName].recordType-meta.xml`
   - Layouts: `force-app/main/default/layouts/[ObjectName]-[LayoutName].layout-meta.xml`

2. Populate template with user requirements

3. Apply naming conventions (see [../../docs/naming-conventions.md](../../docs/naming-conventions.md))

4. Run validation (automatic via hooks or manual)

**Validation Report Format** (6-Category Scoring 0-120):
```
Score: 105/120 ⭐⭐⭐⭐ Very Good
├─ Structure & Format:  20/20 (100%)
├─ Naming Conventions:  18/20 (90%)
├─ Data Integrity:      15/20 (75%)
├─ Security & FLS:      20/20 (100%)
├─ Documentation:       18/20 (90%)
└─ Best Practices:      14/20 (70%)

Issues:
⚠️ [Naming] Field API name should use PascalCase: 'account_status__c' → 'Account_Status__c'
⚠️ [Best Practice] Consider using Global Value Set for reusable picklist
```

### Phase 4: Deployment

**Step 1: Validation**
```
Skill(skill="sf-deployment")
Request: "Deploy metadata at force-app/main/default/objects/[ObjectName] to [target-org] with --dry-run"
```

**Step 2: Deploy** (only if validation succeeds)
```
Skill(skill="sf-deployment")
Request: "Proceed with actual deployment to [target-org]"
```

### Phase 5: Verification

**For Generated Metadata**:
```
✓ Metadata Complete: [MetadataName]
  Type: [CustomObject/CustomField/Profile/etc.] | API: 62.0
  Location: force-app/main/default/[path]
  Validation: PASSED (Score: XX/120)

Next Steps:
  1. Verify in Setup → Object Manager → [Object]
  2. Check Field-Level Security for new fields
  3. Add to Page Layouts if needed
```

**For Queries**:
- Present results in structured format
- Highlight relevant information
- Offer follow-up actions (create field, modify permissions, etc.)

---

## Best Practices (Built-In Enforcement)

### Critical Requirements

**Structure & Format** (20 points):
- Valid XML syntax (-10 if invalid)
- Correct Salesforce namespace: `http://soap.sforce.com/2006/04/metadata` (-5 if missing)
- API version present and >= 62.0 (-5 if outdated)
- Correct file path and naming structure (-5 if wrong)

**Naming Conventions** (20 points):
- Custom objects/fields end with `__c` (-3 each violation)
- Use PascalCase for API names: `Account_Status__c` not `account_status__c` (-2 each)
- Meaningful labels (no abbreviations like `Acct`, `Sts`) (-2 each)
- Relationship names follow pattern: `[ParentObject]_[ChildObjects]` (-3)

**Data Integrity** (20 points):
- Required fields have sensible defaults or validation (-5)
- Number fields have appropriate precision/scale (-3)
- Picklist values properly defined with labels (-3)
- Relationship delete constraints specified (SetNull, Restrict, Cascade) (-3)
- Formula field syntax valid (-5)
- Roll-up summaries reference correct fields (-3)

**Security & FLS** (20 points):
- Field-Level Security considerations documented (-5 if sensitive field exposed)
- Sensitive field types flagged (SSN patterns, Credit Card patterns) (-10)
- Object sharing model appropriate for data sensitivity (-5)
- Permission Sets preferred over Profile modifications (advisory)

**Documentation** (20 points):
- Description present and meaningful on objects/fields (-5 if missing)
- Help text for user-facing fields (-3 each)
- Clear error messages for validation rules (-3)
- Inline comments in complex formulas (-3)

**Best Practices** (20 points):
- Use Permission Sets over Profiles when possible (-3 if Profile-first)
- Avoid hardcoded Record IDs in formulas (-5 if found)
- Use Global Value Sets for reusable picklists (advisory)
- Master-Detail vs Lookup selection appropriate for use case (-3)
- Record Types have associated Page Layouts (-3)

### Scoring Thresholds

| Rating | Score |
|--------|-------|
| ⭐⭐⭐⭐⭐ Excellent | 108-120 |
| ⭐⭐⭐⭐ Very Good | 96-107 |
| ⭐⭐⭐ Good | 84-95 |
| ⭐⭐ Needs Work | 72-83 |
| ⭐ Critical Issues | <72 |

---

## Field Type Selection Guide

| Data Type | Salesforce Field | Use When |
|-----------|------------------|----------|
| Short text | Text | ≤255 characters, single line |
| Long text | Text Area (Long) | >255 characters, multi-line |
| Rich text | Text Area (Rich) | Formatted text with HTML |
| Whole numbers | Number (0 decimals) | Counts, quantities |
| Decimals | Number (with decimals) | Measurements, rates |
| Money | Currency | Monetary values (respects org currency) |
| True/False | Checkbox | Binary options |
| Single choice | Picklist | Predefined options, single select |
| Multiple choice | Multi-Select Picklist | Predefined options, multi-select |
| Date only | Date | Calendar dates without time |
| Date + time | DateTime | Timestamps with timezone |
| Email | Email | Email addresses (validated format) |
| Phone | Phone | Phone numbers (click-to-dial) |
| URL | URL | Web addresses (clickable links) |
| Related record | Lookup | Optional relationship |
| Required parent | Master-Detail | Required relationship, cascade delete |
| Calculated | Formula | Derived from other fields |
| Aggregated | Roll-Up Summary | SUM, COUNT, MIN, MAX from children |

---

## Relationship Decision Matrix

| Scenario | Use | Reason |
|----------|-----|--------|
| Parent optional | Lookup | Child can exist without parent |
| Parent required | Master-Detail | Cascade delete, roll-up summaries |
| Many-to-Many | Junction Object | Two Master-Detail relationships |
| Self-referential | Hierarchical Lookup | Same object (e.g., Account hierarchy) |
| Cross-object formula | Master-Detail or Formula | Access parent fields |

---

## Common Validation Rule Patterns

**Required Field Based on Another**:
```
AND(
    ISPICKVAL(Status__c, 'Closed'),
    ISBLANK(Close_Date__c)
)
// Error: Close Date is required when Status is Closed
```

**Email Format Validation**:
```
NOT(REGEX(Email__c, "^[a-zA-Z0-9._-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"))
// Error: Please enter a valid email address
```

**Future Date Required**:
```
Due_Date__c < TODAY()
// Error: Due Date must be in the future
```

**Cross-Object Validation**:
```
AND(
    NOT(ISBLANK(Account.Type)),
    Account.Type != 'Customer',
    Amount__c > 100000
)
// Error: Opportunities over $100K require Customer account type
```

---

## Cross-Skill Integration

### Invoked BY sf-apex

sf-apex can call sf-metadata to query object/field information before generating triggers:

```
Skill(skill="sf-metadata")
Request: "Query org [alias] to describe object [ObjectName] and list all fields"
```

### Invoked BY sf-flow-builder

sf-flow-builder can call sf-metadata to verify object configuration before creating flows:

```
Skill(skill="sf-metadata")
Request: "Describe object [ObjectName] in org [alias] - show fields, record types, and validation rules"
```

### Invokes sf-deployment

sf-metadata calls sf-deployment for deploying generated metadata:

```
Skill(skill="sf-deployment")
Request: "Deploy metadata at [path] to [target-org] with --dry-run"
```

---

## Metadata Anti-Patterns

| Anti-Pattern | Fix |
|--------------|-----|
| Profile-based FLS | Use Permission Sets for granular access |
| Hardcoded IDs in formulas | Use Custom Settings or Custom Metadata |
| Validation rule without bypass | Add `$Permission.Bypass_Validation__c` check |
| Too many picklist values (>200) | Consider Custom Object instead |
| Auto-number without prefix | Add meaningful prefix: `INV-{0000}` |
| Roll-up on non-M-D | Use trigger-based calculation or DLRS |
| Field label = API name | Use user-friendly labels |
| No description on custom objects | Always document purpose |

---

## sf CLI Quick Reference

### Object & Field Queries

```bash
# Describe standard or custom object
sf sobject describe --sobject Account --target-org [alias] --json

# List all custom objects
sf org list metadata --metadata-type CustomObject --target-org [alias] --json

# List all custom fields on an object
sf org list metadata --metadata-type CustomField --folder Account --target-org [alias] --json
```

### Metadata Operations

```bash
# List all metadata types available
sf org list metadata-types --target-org [alias] --json

# Retrieve specific metadata
sf project retrieve start --metadata CustomObject:Account --target-org [alias]

# Generate package.xml from source
sf project generate manifest --source-dir force-app --name package.xml
```

### Interactive Generation

```bash
# Generate custom object interactively
sf schema generate sobject --label "My Object"

# Generate custom field interactively
sf schema generate field --label "My Field" --object Account
```

---

## Reference Documentation

- [../../docs/metadata-types-reference.md](../../docs/metadata-types-reference.md) - Complete metadata types guide
- [../../docs/field-types-guide.md](../../docs/field-types-guide.md) - Field type selection guide
- [../../docs/fls-best-practices.md](../../docs/fls-best-practices.md) - Field-Level Security patterns
- [../../docs/profile-permission-guide.md](../../docs/profile-permission-guide.md) - Profiles vs Permission Sets
- [../../docs/naming-conventions.md](../../docs/naming-conventions.md) - Naming standards
- [../../docs/sf-cli-commands.md](../../docs/sf-cli-commands.md) - sf CLI reference

---

## Dependencies

- **sf-deployment** (optional): Required for deploying metadata to Salesforce orgs
  - If not installed, metadata will be created locally but cannot be deployed via `Skill(skill="sf-deployment")`
  - Install: `/plugin install github:Jaganpro/sf-skills/sf-deployment`

## Notes

- **API Version**: 62.0 required
- **Permission Sets Preferred**: Always recommend Permission Sets over Profile modifications
- **Scoring**: Block deployment if score < 72

---

## License

MIT License. See [LICENSE](LICENSE) file.
Copyright (c) 2024-2025 Jag Valaiyapathy
