# Skill Scoring Overview

All sf-skills use point-based validation scoring with star ratings.

## Rating Thresholds (Universal)

| Rating | Percentage |
|--------|------------|
| ⭐⭐⭐⭐⭐ Excellent | 90%+ |
| ⭐⭐⭐⭐ Very Good | 80-89% |
| ⭐⭐⭐ Good | 70-79% |
| ⭐⭐ Needs Work | 60-69% |
| ⭐ Critical | <60% (deployment blocked) |

## Skill-Specific Scoring

| Skill | Max | Block | Categories |
|-------|-----|-------|------------|
| sf-apex | 150 | <67 | Bulk, Security, Testing, Architecture, Clean Code, Error, Performance, Docs |
| sf-flow | 110 | <88 | Design, Logic, Architecture, Performance, Error, Security |
| sf-metadata | 120 | <72 | Structure, Naming, Integrity, Security, Docs, Best Practices |
| sf-data | 130 | <78 | Query, Bulk, Integrity, Security, Tests, Cleanup, Docs |
| sf-integration | 120 | <72 | Credential, Callout, Events, CDC, Security, Docs |
| sf-connected-apps | 120 | <72 | Structure, OAuth, Security, Compliance, Docs, Best Practices |
| sf-ai-agentforce | 100 | <60 | Syntax, Config, Topics, Actions, Variables, Deployment |
| sf-diagram | 80 | <48 | Accuracy, Notation, Styling, Completeness, Clarity |

## Output Format

```
Score: XX/MAX ⭐⭐⭐⭐ Rating
├─ Category 1: XX/YY
└─ Category 2: XX/YY
```

**Block Rule**: Score below threshold blocks deployment with required fixes.
