---
name: sf-debug
description: >
  Salesforce debugging and troubleshooting skill with log analysis, governor limit
  detection, and agentic fix suggestions. Parse debug logs, identify performance
  bottlenecks, analyze stack traces, and automatically suggest fixes.
license: MIT
metadata:
  version: "1.1.0"
  author: "Jag Valaiyapathy"
  scoring: "100 points across 5 categories"
hooks:
  PreToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: "python3 ${SHARED_HOOKS}/scripts/guardrails.py"
          timeout: 5000
  PostToolUse:
    - matcher: Bash
      hooks:
        - type: command
          command: "python3 ${SKILL_HOOKS}/parse-debug-log.py"
          timeout: 10000
    - matcher: "Write|Edit"
      hooks:
        - type: command
          command: "python3 ${SHARED_HOOKS}/suggest-related-skills.py sf-debug"
          timeout: 5000
  SubagentStop:
    - type: command
      command: "python3 ${SHARED_HOOKS}/scripts/chain-validator.py sf-debug"
      timeout: 5000
---

# sf-debug: Salesforce Debug Log Analysis & Troubleshooting

Expert debugging engineer specializing in Apex debug log analysis, governor limit detection, performance optimization, and root cause analysis. Parse logs, identify issues, and automatically suggest fixes.

## Core Responsibilities

1. **Log Analysis**: Parse and analyze Apex debug logs for issues
2. **Governor Limit Detection**: Identify SOQL, DML, CPU, and heap limit concerns
3. **Performance Analysis**: Find slow queries, expensive operations, and bottlenecks
4. **Stack Trace Interpretation**: Parse exceptions and identify root causes
5. **Agentic Fix Suggestions**: Automatically suggest code fixes based on issues found
6. **Query Plan Analysis**: Analyze SOQL query performance and selectivity

## Workflow (5-Phase Pattern)

### Phase 1: Log Collection

Use **AskUserQuestion** to gather:
- Debug context (deployment failure, test failure, runtime error, performance issue)
- Target org alias
- User/Transaction ID if known
- Time range of issue

**Then**:
1. List available logs: `sf apex list log --target-org [alias]`
2. Fetch specific log or tail real-time
3. Create TodoWrite tasks

### Phase 2: Log Retrieval

**List Recent Logs**:
```bash
sf apex list log --target-org [alias] --json
```

**Get Specific Log**:
```bash
sf apex get log --log-id 07Lxx0000000000 --target-org [alias]
```

**Tail Logs Real-Time**:
```bash
sf apex tail log --target-org [alias] --color
```

**Set Debug Level**:
```bash
sf apex log tail --debug-level FINE --target-org [alias]
```

### Phase 3: Log Analysis

Parse the debug log and analyze:

```
┌─────────────────────────────────────────────────────────────────┐
│                    DEBUG LOG ANALYSIS                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. EXECUTION OVERVIEW                                           │
│     ├── Transaction type (trigger, flow, REST, batch)            │
│     ├── Total execution time                                     │
│     └── Entry point identification                               │
│                                                                  │
│  2. GOVERNOR LIMIT ANALYSIS                                      │
│     ├── SOQL Queries: X/100                                      │
│     ├── DML Statements: X/150                                    │
│     ├── DML Rows: X/10,000                                       │
│     ├── CPU Time: X ms /10,000 ms                                │
│     ├── Heap Size: X bytes /6,000,000                            │
│     └── Callouts: X/100                                          │
│                                                                  │
│  3. PERFORMANCE HOTSPOTS                                         │
│     ├── Slowest SOQL queries (execution time)                    │
│     ├── Non-selective queries (full table scan)                  │
│     ├── Expensive operations (loops, iterations)                 │
│     └── External callout timing                                  │
│                                                                  │
│  4. EXCEPTIONS & ERRORS                                          │
│     ├── Exception type                                           │
│     ├── Stack trace                                              │
│     ├── Line number                                              │
│     └── Root cause identification                                │
│                                                                  │
│  5. RECOMMENDATIONS                                              │
│     ├── Immediate fixes                                          │
│     ├── Optimization suggestions                                 │
│     └── Architecture improvements                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Phase 4: Issue Identification & Fix Suggestions

**Governor Limit Analysis Decision Tree**:

| Issue | Detection Pattern | Fix Strategy |
|-------|-------------------|--------------|
| SOQL in Loop | `SOQL_EXECUTE_BEGIN` inside `METHOD_ENTRY` repeated | Query before loop, use Map for lookups |
| DML in Loop | `DML_BEGIN` inside `METHOD_ENTRY` repeated | Collect in List, single DML after loop |
| Non-Selective Query | `Query plan` shows > 100,000 rows | Add indexed filter or LIMIT |
| CPU Limit | `CPU_TIME` approaching 10000 | Optimize algorithms, use async |
| Heap Limit | `HEAP_ALLOCATE` approaching 6MB | Reduce collection sizes, use FOR loops |
| Callout Limit | `CALLOUT_EXTERNAL_ENTRY` count > 90 | Batch callouts, use Queueable |

**Auto-Fix Command**:
```
Skill(skill="sf-apex", args="Fix [issue type] in [ClassName] at line [lineNumber]")
```

### Phase 5: Fix Implementation

1. **Generate fix** using sf-apex skill
2. **Deploy fix** using sf-deploy skill
3. **Verify fix** by re-running and checking logs
4. **Report results**

---

## Best Practices (100-Point Scoring)

| Category | Points | Key Rules |
|----------|--------|-----------|
| **Root Cause** | 25 | Correctly identify the actual cause, not symptoms |
| **Fix Accuracy** | 25 | Suggested fix addresses the root cause |
| **Performance Impact** | 20 | Fix improves performance, doesn't introduce new issues |
| **Completeness** | 15 | All related issues identified, not just the first one |
| **Clarity** | 15 | Explanation is clear and actionable |

**Scoring Thresholds**:
```
⭐⭐⭐⭐⭐ 90-100 pts → Expert analysis with optimal fix
⭐⭐⭐⭐   80-89 pts  → Good analysis, effective fix
⭐⭐⭐    70-79 pts  → Acceptable analysis, partial fix
⭐⭐      60-69 pts  → Basic analysis, may miss issues
⭐        <60 pts   → Incomplete analysis
```

---

## Debug Log Anatomy

### Log Structure

```
XX.X (XXXXX)|TIMESTAMP|EVENT_TYPE|[PARAMS]|DETAILS
```

### Key Event Types

| Event | Meaning | Important For |
|-------|---------|---------------|
| `EXECUTION_STARTED` | Transaction begins | Context identification |
| `CODE_UNIT_STARTED` | Method/trigger entry | Call stack tracing |
| `SOQL_EXECUTE_BEGIN` | Query starts | Query analysis |
| `SOQL_EXECUTE_END` | Query ends | Query timing |
| `DML_BEGIN` | DML starts | DML analysis |
| `DML_END` | DML ends | DML timing |
| `EXCEPTION_THROWN` | Exception occurs | Error detection |
| `FATAL_ERROR` | Transaction fails | Critical issues |
| `LIMIT_USAGE` | Limit snapshot | Governor limits |
| `HEAP_ALLOCATE` | Heap allocation | Memory issues |
| `CPU_TIME` | CPU time used | Performance |
| `CALLOUT_EXTERNAL_ENTRY` | Callout starts | External calls |

### Log Levels

| Level | Shows |
|-------|-------|
| NONE | Nothing |
| ERROR | Errors only |
| WARN | Warnings and errors |
| INFO | General info (default) |
| DEBUG | Detailed debug info |
| FINE | Very detailed |
| FINER | Method entry/exit |
| FINEST | Everything |

---

## Common Issues & Solutions

### 1. SOQL Query in Loop

**Detection**:
```
|SOQL_EXECUTE_BEGIN|[line 45]
|SOQL_EXECUTE_END|[1 row]
... (repeats 50+ times)
```

**Analysis Output**:
```
🔴 CRITICAL: SOQL Query in Loop Detected
   Location: AccountService.cls, line 45
   Impact: 50 queries executed, approaching 100 limit
   Pattern: SELECT inside for loop

📝 RECOMMENDED FIX:
   Move query BEFORE loop, use Map for lookups:

   // Before (problematic)
   for (Account acc : accounts) {
       Contact c = [SELECT Id FROM Contact WHERE AccountId = :acc.Id LIMIT 1];
   }

   // After (bulkified)
   Map<Id, Contact> contactsByAccount = new Map<Id, Contact>();
   for (Contact c : [SELECT Id, AccountId FROM Contact WHERE AccountId IN :accountIds]) {
       contactsByAccount.put(c.AccountId, c);
   }
   for (Account acc : accounts) {
       Contact c = contactsByAccount.get(acc.Id);
   }
```

### 2. Non-Selective Query

**Detection**:
```
|SOQL_EXECUTE_BEGIN|[line 23]|SELECT Id FROM Lead WHERE Status = 'Open'
|SOQL_EXECUTE_END|[250000 rows queried]
```

**Analysis Output**:
```
🟠 WARNING: Non-Selective Query Detected
   Location: LeadService.cls, line 23
   Rows Scanned: 250,000
   Filter Field: Status (not indexed)

📝 RECOMMENDED FIX:
   Option 1: Add indexed field to WHERE clause
   Option 2: Create custom index on Status field
   Option 3: Add LIMIT clause if not all records needed

   // Before
   List<Lead> leads = [SELECT Id FROM Lead WHERE Status = 'Open'];

   // After (with additional selective filter)
   List<Lead> leads = [SELECT Id FROM Lead
                       WHERE Status = 'Open'
                       AND CreatedDate = LAST_N_DAYS:30
                       LIMIT 10000];
```

### 3. CPU Time Limit

**Detection**:
```
|LIMIT_USAGE_FOR_NS|CPU_TIME|9500|10000
```

**Analysis Output**:
```
🔴 CRITICAL: CPU Time Limit Approaching (95%)
   Used: 9,500 ms
   Limit: 10,000 ms (sync) / 60,000 ms (async)

📝 ANALYSIS:
   Top CPU consumers:
   1. StringUtils.formatAll() - 3,200 ms (line 89)
   2. CalculationService.compute() - 2,800 ms (line 156)
   3. ValidationHelper.validateAll() - 1,500 ms (line 45)

📝 RECOMMENDED FIX:
   1. Move heavy computation to @future or Queueable
   2. Optimize algorithms (O(n²) → O(n))
   3. Cache repeated calculations
   4. Use formula fields instead of Apex where possible
```

### 4. Heap Size Limit

**Detection**:
```
|HEAP_ALLOCATE|[5800000]
|LIMIT_USAGE_FOR_NS|HEAP_SIZE|5800000|6000000
```

**Analysis Output**:
```
🔴 CRITICAL: Heap Size Limit Approaching (97%)
   Used: 5.8 MB
   Limit: 6 MB (sync) / 12 MB (async)

📝 ANALYSIS:
   Large allocations detected:
   1. Line 34: List<Account> - 2.1 MB (50,000 records)
   2. Line 78: Map<Id, String> - 1.8 MB
   3. Line 112: String concatenation - 1.2 MB

📝 RECOMMENDED FIX:
   1. Use SOQL FOR loops instead of querying all at once
   2. Process in batches of 200 records
   3. Use transient keyword for variables not needed in view state
   4. Clear collections when no longer needed

   // Before
   List<Account> allAccounts = [SELECT Id, Name FROM Account];

   // After (SOQL FOR loop - doesn't load all into heap)
   for (Account acc : [SELECT Id, Name FROM Account]) {
       // Process one at a time
   }
```

### 5. Exception Analysis

**Detection**:
```
|EXCEPTION_THROWN|[line 67]|System.NullPointerException: Attempt to de-reference a null object
|FATAL_ERROR|System.NullPointerException: Attempt to de-reference a null object
```

**Analysis Output**:
```
🔴 EXCEPTION: System.NullPointerException
   Location: ContactService.cls, line 67
   Message: Attempt to de-reference a null object

📝 STACK TRACE ANALYSIS:
   ContactService.getContactDetails() - line 67
   └── AccountController.loadData() - line 34
       └── trigger AccountTrigger - line 5

📝 ROOT CAUSE:
   Variable 'contact' is null when accessing 'contact.Email'
   Likely scenario: Query returned no results

📝 RECOMMENDED FIX:
   // Before
   Contact contact = [SELECT Email FROM Contact WHERE AccountId = :accId LIMIT 1];
   String email = contact.Email;  // FAILS if no contact found

   // After (null-safe)
   List<Contact> contacts = [SELECT Email FROM Contact WHERE AccountId = :accId LIMIT 1];
   String email = contacts.isEmpty() ? null : contacts[0].Email;

   // Or using safe navigation (API 62.0+)
   Contact contact = [SELECT Email FROM Contact WHERE AccountId = :accId LIMIT 1];
   String email = contact?.Email;
```

---

## CLI Command Reference

### Log Management

| Command | Purpose |
|---------|---------|
| `sf apex list log` | List available logs |
| `sf apex get log` | Download specific log |
| `sf apex tail log` | Stream logs real-time |
| `sf apex log delete` | Delete logs |

### Debug Level Control

```bash
# Create trace flag for user
sf data create record \
  --sobject TraceFlag \
  --values "TracedEntityId='005xx000000000' LogType='USER_DEBUG' DebugLevelId='7dlxx000000000' StartDate='2024-01-01T00:00:00' ExpirationDate='2024-01-02T00:00:00'" \
  --target-org my-sandbox

# Set default debug level
sf config set org-api-version=62.0
```

### Query Plan Analysis

```bash
# Use Developer Console or the REST API explain endpoint
ENCODED_QUERY=$(python3 - <<'PY'
import urllib.parse
print(urllib.parse.quote("SELECT Id FROM Account WHERE Name = 'Test'", safe=""))
PY
)

sf api request rest "/services/data/v65.0/query/?explain=${ENCODED_QUERY}" \
  --target-org my-sandbox
```

---

## Agentic Debug Loop

When enabled, sf-debug will automatically:

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENTIC DEBUG LOOP                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. Fetch debug logs from the failing operation                  │
│  2. Parse logs and identify all issues                           │
│  3. Prioritize issues by severity:                               │
│     🔴 Critical: Limits exceeded, exceptions                     │
│     🟠 Warning: Approaching limits, slow queries                 │
│     🟡 Info: Optimization opportunities                          │
│  4. For each critical issue:                                     │
│     a. Read the source file at identified line                   │
│     b. Generate fix using sf-apex skill                          │
│     c. Deploy fix using sf-deploy skill                          │
│     d. Re-run operation and check new logs                       │
│  5. Report final status and remaining warnings                   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Cross-Skill Integration

| Skill | When to Use | Example |
|-------|-------------|---------|
| sf-apex | Generate fixes for identified issues | `Skill(skill="sf-apex", args="Fix NullPointerException in ContactService line 67")` |
| sf-testing | Run tests to reproduce issues | `Skill(skill="sf-testing", args="Run AccountServiceTest to generate debug logs")` |
| sf-deploy | Deploy fixes | `Skill(skill="sf-deploy", args="Deploy ContactService.cls to sandbox")` |
| sf-data | Create test data for debugging | `Skill(skill="sf-data", args="Create Account with specific conditions")` |

---

## Performance Benchmarks

### Healthy Limits

| Resource | Warning Threshold | Critical Threshold |
|----------|-------------------|-------------------|
| SOQL Queries | 80/100 (80%) | 95/100 (95%) |
| DML Statements | 120/150 (80%) | 145/150 (97%) |
| CPU Time | 8,000/10,000 ms | 9,500/10,000 ms |
| Heap Size | 4.8/6 MB | 5.7/6 MB |
| Callouts | 80/100 | 95/100 |

### Query Performance

| Category | Acceptable | Needs Optimization |
|----------|------------|-------------------|
| Query Time | < 100ms | > 500ms |
| Rows Scanned | < 10,000 | > 100,000 |
| Selectivity | Indexed filter | Full table scan |

---

## Documentation

| Document | Description |
|----------|-------------|
| [debug-log-reference.md](docs/debug-log-reference.md) | Complete debug log event reference |
| [cli-commands.md](docs/cli-commands.md) | SF CLI debugging commands |
| [benchmarking-guide.md](docs/benchmarking-guide.md) | Dan Appleman's technique, real-world benchmarks |
| [log-analysis-tools.md](docs/log-analysis-tools.md) | Apex Log Analyzer, manual analysis patterns |

## Templates

| Template | Description |
|----------|-------------|
| [cpu-heap-optimization.cls](templates/cpu-heap-optimization.cls) | CPU and heap optimization patterns |
| [benchmarking-template.cls](templates/benchmarking-template.cls) | Ready-to-run benchmark comparisons |
| [soql-in-loop-fix.cls](templates/soql-in-loop-fix.cls) | SOQL bulkification pattern |
| [dml-in-loop-fix.cls](templates/dml-in-loop-fix.cls) | DML bulkification pattern |
| [null-pointer-fix.cls](templates/null-pointer-fix.cls) | Null-safe patterns |

---

## Credits

See [CREDITS.md](CREDITS.md) for acknowledgments of community resources that shaped this skill.

---

## Dependencies

**Required**: Target org with `sf` CLI authenticated
**Recommended**: sf-apex (for auto-fix), sf-testing (for reproduction), sf-deploy (for deploying fixes)

Install: `/plugin install github:Jaganpro/sf-skills/sf-debug`

---

## License

MIT License. See [LICENSE](LICENSE) file.
Copyright (c) 2024-2025 Jag Valaiyapathy
