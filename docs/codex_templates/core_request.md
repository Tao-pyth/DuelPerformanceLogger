# Codex Template: Core Request

Use this template for Codex automation covering core functionality (migrations, updater, telemetry, backend logic).

---

## Summary
- **Module / Area:**
- **Problem Statement:**
- **Target Version:** `DPL.x.y.z`

## Requirements
- [ ] Changes confined to `app/function/core/` unless specified
- [ ] Migrations are idempotent and logged
- [ ] Updater contract (`Updater.exe` CLI) respected
- [ ] Telemetry schemas updated in `03_icd_core.md`
- [ ] Tests cover new branches (`pytest -m core`)

## Inputs
- Current config / schema state:
- Related Jira tickets:

## Acceptance Criteria
1. 
2. 
3. 

## Testing Commands
- `pytest -m core`
- `pytest -m migration`
- `python scripts/tools/migration_smoke.py`

## Deployment / Rollout
- Required migrations:
- Manifest updates needed:
- Rollback plan:

**Last Updated:** 2025-10-12
