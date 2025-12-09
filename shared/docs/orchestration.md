# Multi-Skill Orchestration Order

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  CORRECT MULTI-SKILL ORCHESTRATION ORDER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. sf-metadata  → Create object/field definitions (LOCAL files)            │
│  2. sf-flow      → Create flow definitions (LOCAL files)                    │
│  3. sf-deploy    → Deploy all metadata to org (REMOTE)                      │
│  4. sf-data      → Create test data (REMOTE - objects must exist!)          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Why Order Matters

| Step | Depends On | Fails If Wrong Order |
|------|------------|---------------------|
| sf-flow | sf-metadata | Flow references non-existent field |
| sf-deploy | sf-metadata, sf-flow | Nothing to deploy |
| sf-data | sf-deploy | `SObject type 'X' not supported` |

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `SObject type 'X' not supported` | Object not deployed | Run sf-deploy first |
| `Field does not exist` | FLS or missing field | Deploy field + Permission Set |
| `Flow is invalid` | Missing object reference | Deploy objects BEFORE flows |
