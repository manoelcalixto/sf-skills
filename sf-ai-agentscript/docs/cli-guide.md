# Agent Script CLI Quick Reference

> Pro-Code Lifecycle: Git, CI/CD, and CLI for Agent Development

---

## The sf agent Commands

| Command | Purpose | Example |
|---------|---------|---------|
| `sf agent retrieve` | Pull agent from org | `sf agent retrieve --name MyAgent --target-org sandbox` |
| `sf agent validate` | Check syntax before deploy | `sf agent validate --source-dir ./my-agent` |
| `sf agent deploy` | Push to target org | `sf agent deploy --source-dir ./my-agent --target-org prod` |
| `sf agent test run` | Run batch tests | `sf agent test run --name MyAgent --test-suite AllTests` |

---

## Authoring Bundle Structure

```
pronto-refund/
├── main.agent          # Your Agent Script (REQUIRED)
├── agent-meta.xml      # Salesforce metadata (REQUIRED)
├── topics/             # Topic definitions
│   ├── refund_request.topic
│   └── escalation.topic
└── actions/            # Action specifications
    └── process_refund.action
```

### agent-meta.xml Fields

| Field | Description | Example |
|-------|-------------|---------|
| `label` | Human-readable name | `Pronto Refund Agent` |
| `status` | Active, Inactive, Draft | `Active` |
| `apiVersion` | SF API version | `62.0` |
| `description` | Agent description | `Handles refund requests` |

---

## Pro-Code Workflow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ 1 Retrieve  │ →  │ 2 Edit      │ →  │ 3 Validate  │ →  │ 4 Deploy    │
│ Pull agent  │    │ CLI/editor  │    │ Check syntax│    │ Push to prod│
│ from org    │    │ + Claude    │    │             │    │             │
└─────────────┘    └─────────────┘    └─────────────┘    └─────────────┘
```

### Step 1: Retrieve

```bash
# Retrieve from sandbox
sf agent retrieve --name ProntoRefund --target-org sandbox
```

### Step 2: Edit

```bash
# Edit the agent script
vim ./ProntoRefund/main.agent
```

### Step 3: Validate

```bash
# Validate syntax before deployment
sf agent validate --source-dir ./ProntoRefund

# Validate authoring bundle specifically
sf agent validate authoring-bundle --source-dir ./ProntoRefund
```

### Step 4: Deploy

```bash
# Deploy to production
sf agent deploy --source-dir ./ProntoRefund --target-org prod
```

---

## Testing Commands

```bash
# Run against draft version
sf agent test run --name MyAgent --version draft

# Run against committed version
sf agent test run --name MyAgent --version v1.0

# Run specific test suite
sf agent test run --name MyAgent --test-suite Regression
```

---

## Validation Commands

```bash
# Validate syntax
sf agent validate --source-dir ./my-agent

# Check specific version
sf agent test run --name MyAgent --version v1.0 --test-suite Regression
```

### Common Validation Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `Internal Error, try again later` | Invalid `default_agent_user` | Query for Einstein Agent Users |
| `SyntaxError: You cannot mix spaces and tabs` | Mixed indentation | Use consistent spacing |
| `Transition to undefined topic "@topic.X"` | Typo in topic name | Check spelling |
| `Variables cannot be both mutable AND linked` | Conflicting modifiers | Choose one modifier |

---

## Einstein Agent User Setup

### Query Existing Users

```bash
sf data query --query "SELECT Username FROM User WHERE Profile.Name = 'Einstein Agent User' AND IsActive = true"
```

### Username Format

```
agent_user@<org-id>.ext
```

Example: `agent_user@00drt00000limwjmal.ext`

### Get Org ID

```bash
sf org display --json | jq -r '.result.id'
```

---

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Agent Testing
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Validate Agent
        run: sf agent validate --source-dir ./agents/my-agent
      - name: Run Tests
        run: sf agent test run --name MyAgent --test-suite CI
```

---

## Deployment Pipeline

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  Sandbox    │ ───▶ │   Staging   │ ───▶ │ Production  │
│   v1.3.0    │      │  Validate   │      │   v1.3.0    │
└─────────────┘      └─────────────┘      └─────────────┘
```

### 6-Step Pipeline

1. **Retrieve from Sandbox** - Pull latest agent bundle
2. **Validate Syntax** - Check Agent Script for errors
3. **Run Tests** - Execute automated agent tests
4. **Code Review** - Automated best practices checks
5. **Deploy to Production** - Push validated bundle
6. **Verify Deployment** - Confirm agent is active

---

## Three-Phase Lifecycle

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   ✏️ Draft   │  →   │  🔒 Commit  │  →   │  ✅ Activate │
│   EDITABLE  │      │  READ-ONLY  │      │    LIVE     │
└─────────────┘      └─────────────┘      └─────────────┘
```

| Phase | Capabilities |
|-------|--------------|
| **Draft** | Edit freely, preview, run batch tests |
| **Commit** | Script frozen, version assigned, bundle compiled |
| **Activate** | Assign to Connections, go live, monitor |

> **Key Insight**: Commit doesn't deploy - it freezes. Activate makes it live.
