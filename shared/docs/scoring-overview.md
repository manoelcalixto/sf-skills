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

## Skill-Specific Maximums

| Skill | Max Points | Categories | Block Threshold |
|-------|------------|------------|-----------------|
| sf-apex | 150 | 8 (Bulk, Security, Testing, Architecture, Clean Code, Error, Performance, Docs) | <67 |
| sf-flow | 110 | 6 (Design, Logic, Architecture, Performance, Error, Security) | <88 |
| sf-metadata | 120 | 6 (Structure, Naming, Integrity, Security, Docs, Best Practices) | <72 |
| sf-data | 130 | 7 (Query, Bulk, Integrity, Security, Tests, Cleanup, Docs) | <78 |

## Validation Output Format

```
Score: XX/MAX ⭐⭐⭐⭐ Rating
├─ Category 1: XX/YY (ZZ%)
├─ Category 2: XX/YY (ZZ%)
└─ ...
```
