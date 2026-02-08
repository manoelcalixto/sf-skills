# TDD Validation Framework

Test-Driven Development validation framework for `sf-ai-agentforce-observability` skill.

## Overview

This framework validates the skill's CLI commands and API integrations against SKILL.md claims through a tiered pytest test suite.

## Quick Start

```bash
# Install dependencies
pip install -r validation/requirements.txt

# Run offline tests only (no Salesforce connection needed)
python3 validation/scripts/run_validation.py --offline

# Run full validation against live org
python3 validation/scripts/run_validation.py --org Vivint-DevInt

# Run specific tier
python3 validation/scripts/run_validation.py --tier T1 --org Vivint-DevInt
```

## Test Tiers

| Tier | Category | Points | Description |
|------|----------|--------|-------------|
| T1 | Auth & Connectivity | 25 | JWT auth, consumer key resolution, API access |
| T2 | Extraction Commands | 30 | extract, extract-tree, extract-incremental, count |
| T3 | Analysis Commands | 20 | analyze, debug-session, topics, quality-report |
| T4 | Data Model/Schema | 15 | DMO names, field casing, Parquet structure |
| T5 | Negative/Error Cases | 10 | Auth failures, invalid arguments |

**Pass Threshold:** ≥80 points

## Directory Structure

```
validation/
├── README.md                    # This file
├── VALIDATION.md               # Tracking history
├── scenario_registry.json      # Test metadata & scoring
├── requirements.txt            # Dependencies
├── conftest.py                 # Shared pytest fixtures
│
├── scenarios/
│   ├── tier1_connectivity/     # Auth & API tests
│   │   ├── test_auth_resolution.py
│   │   ├── test_api_connectivity.py
│   │   └── test_auth_negative.py
│   │
│   ├── tier2_extraction/       # CLI extraction tests
│   │   ├── test_extract_basic.py
│   │   ├── test_extract_filtered.py
│   │   ├── test_extract_tree.py
│   │   ├── test_extract_incremental.py
│   │   └── test_count_command.py
│   │
│   ├── tier3_analysis/         # CLI analysis tests
│   │   ├── test_analyze.py
│   │   ├── test_debug_session.py
│   │   ├── test_topics.py
│   │   └── test_quality_report.py
│   │
│   ├── tier4_schema/           # Schema validation
│   │   ├── test_dmo_schemas.py
│   │   └── test_parquet_output.py
│   │
│   └── tier5_negative/         # Error handling
│       ├── test_auth_failures.py
│       └── test_invalid_args.py
│
├── fixtures/                   # Sample Parquet data
│   ├── sessions/
│   ├── interactions/
│   ├── steps/
│   └── messages/
│
└── scripts/
    ├── run_validation.py       # Main runner
    └── generate_report.py      # Update VALIDATION.md
```

## Running Tests

### With pytest directly

```bash
# All tests
cd sf-ai-agentforce-observability
pytest validation/scenarios -v

# Offline only
pytest validation/scenarios -v --offline

# Specific tier
pytest validation/scenarios -v -m tier1

# Specific test file
pytest validation/scenarios/tier1_connectivity/test_auth_resolution.py -v
```

### With validation runner

```bash
# Full validation with scoring
python3 validation/scripts/run_validation.py --org Vivint-DevInt

# Offline mode
python3 validation/scripts/run_validation.py --offline

# JSON output
python3 validation/scripts/run_validation.py --org Vivint-DevInt --json

# Generate report
python3 validation/scripts/run_validation.py --org Vivint-DevInt --report
```

## Test Markers

Tests are marked for selective execution:

- `@pytest.mark.live_api` - Requires Salesforce connection
- `@pytest.mark.offline` - Uses local fixtures only
- `@pytest.mark.slow` - Long-running tests
- `@pytest.mark.tier1` through `@pytest.mark.tier5` - Tier categorization

## Fixtures

The `conftest.py` provides shared fixtures:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `org_alias` | session | Org alias from CLI or default |
| `auth_client` | session | Authenticated Data360Auth |
| `data_client` | function | Data360Client for queries |
| `mock_auth` | function | Mocked auth for offline tests |
| `temp_output_dir` | function | Temporary directory for output |
| `sample_data_dir` | session | Path to fixture Parquet data |
| `cli_runner` | function | Click CliRunner for CLI tests |
| `cli_app` | function | CLI application entry point |

## Scoring

Each tier contributes points based on test pass rate:

```
Tier Score = (Tests Passed / Total Tests) × Tier Weight
Total Score = Sum of Tier Scores
```

| Result | Score Range |
|--------|-------------|
| PASS | ≥80% |
| WARN | 70-79% |
| FAIL | <70% |

## Adding Tests

1. Create test file in appropriate tier directory
2. Use pytest markers for categorization
3. Use fixtures from conftest.py
4. Add test to scenario_registry.json if tracking points

Example test:

```python
import pytest

@pytest.mark.tier1
@pytest.mark.offline
class TestNewFeature:
    def test_something(self, sample_data_dir):
        # Test implementation
        assert True
```

## Integration with test_v65.py

The existing `scripts/test_v65.py` provides quick smoke testing:

| test_v65.py Level | Validation Tier |
|-------------------|-----------------|
| Level 1-2 | T1 |
| Level 3-5 | T1 |
| Level 6-7 | T2 |

Use `test_v65.py` for quick checks; use this framework for comprehensive validation.

## Troubleshooting

### Tests skipped due to missing auth

Ensure auth files exist:
```bash
ls ~/.sf/jwt/${ORG_ALIAS}*.key
ls ~/.sf/jwt/${ORG_ALIAS}*.consumer-key
```

### Fixture data not found

Fixtures are auto-created on first run. If issues persist:
```bash
rm -rf validation/fixtures
python3 validation/scripts/run_validation.py --offline
```

### Import errors

Ensure you're running from the skill root:
```bash
cd sf-ai-agentforce-observability
pytest validation/scenarios -v
```
