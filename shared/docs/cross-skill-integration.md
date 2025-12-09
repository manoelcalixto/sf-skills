# Cross-Skill Integration Reference

## Quick Reference Table

| From Skill | To Skill | When | Example |
|------------|----------|------|---------|
| sf-apex | sf-metadata | Discover object/fields before coding | "Describe Invoice__c" |
| sf-apex | sf-data | Generate test records (251+) | "Create 251 Accounts for bulk testing" |
| sf-apex | sf-deploy | Deploy and run tests | "Deploy with RunLocalTests" |
| sf-flow | sf-metadata | Verify object structure | "Describe Invoice__c fields" |
| sf-flow | sf-data | Generate trigger test data | "Create 200 Accounts with criteria X" |
| sf-flow | sf-deploy | Deploy and activate | "Deploy flow with --dry-run" |
| sf-data | sf-metadata | Discover object structure | "Describe Custom_Object__c fields" |
| sf-metadata | sf-deploy | Deploy metadata to org | "Deploy objects with --dry-run" |

## Installation

All skills are optional and independent. Install as needed:
```
/plugin install github:Jaganpro/sf-skills/sf-deploy
/plugin install github:Jaganpro/sf-skills/sf-metadata
/plugin install github:Jaganpro/sf-skills/sf-data
/plugin install github:Jaganpro/sf-skills/sf-apex
/plugin install github:Jaganpro/sf-skills/sf-flow
```

## Invocation Pattern

```
Skill(skill="sf-[name]")
Request: "[your request]"
```
