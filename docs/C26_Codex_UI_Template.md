# C26. Codex UI Template
Use this template when filing Codex tasks for UI changes such as KV updates, screen controllers, or visual polish.

## Table of Contents
- [Summary](#summary)
- [Requirements](#requirements)
- [Assets](#assets)
- [Acceptance Criteria](#acceptance-criteria)
- [Testing Commands](#testing-commands)
- [Rollout / Notes](#rollout-notes)

## <a id="summary"></a>Summary
- **Feature / Screen:**
- **Goal:**
- **Design Reference:** (link to spec, e.g., [`C27_UI_Spec_MenuScreen.md`](C27_UI_Spec_MenuScreen.md))

## <a id="requirements"></a>Requirements
- [ ] Update KV files under `app/function/ui/kv/`.
- [ ] Adjust controller logic in `app/function/ui/screens/`.
- [ ] Source theme colours from `ui/theme.py`.
- [ ] Add localisation keys under `strings.menu.*` when needed.
- [ ] Refresh snapshot tests (`pytest -m snapshot`).

## <a id="assets"></a>Assets
- Mockups / screenshots:
- Icon or font updates:

## <a id="acceptance-criteria"></a>Acceptance Criteria
1.
2.
3.

## <a id="testing-commands"></a>Testing Commands
- `pytest -m snapshot`
- `python -m app.tools.kv_lint`

## <a id="rollout-notes"></a>Rollout / Notes
- Impacted release: `DPL.x.y.z`
- Feature flag / config toggle:
- Telemetry events to emit:

**Last Updated:** 2025-10-12
