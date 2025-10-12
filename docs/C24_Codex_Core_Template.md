# C24. Codex Core Template
Use this template for Codex automation that touches migrations, updater integration, telemetry, or other core backend logic.

## Table of Contents
- [Summary](#summary)
- [Requirements](#requirements)
- [Inputs](#inputs)
- [Acceptance Criteria](#acceptance-criteria)
- [Testing Commands](#testing-commands)
- [Deployment / Rollout](#deployment-rollout)

## <a id="summary"></a>Summary
- **Module / Area:**
- **Problem Statement:**
- **Target Version:** `DPL.x.y.z`

## <a id="requirements"></a>Requirements
- [ ] Confine changes to `app/function/core/` unless explicitly approved.
- [ ] Keep migrations idempotent and ensure they log via `core.migrations.runner`.
- [ ] Respect the `Updater.exe` CLI contract defined in [`A03_Interface_Control_Core.md`](A03_Interface_Control_Core.md).
- [ ] Update telemetry schemas documented in [`A03_Interface_Control_Core.md`](A03_Interface_Control_Core.md).
- [ ] Cover new branches with tests (`pytest -m core`).

## <a id="inputs"></a>Inputs
- Current config / schema state:
- Related Jira tickets:

## <a id="acceptance-criteria"></a>Acceptance Criteria
1.
2.
3.

## <a id="testing-commands"></a>Testing Commands
- `pytest -m core`
- `pytest -m migration`
- `python scripts/tools/migration_smoke.py`

## <a id="deployment-rollout"></a>Deployment / Rollout
- Required migrations:
- Manifest updates needed:
- Rollback plan:

**Last Updated:** 2025-10-12
