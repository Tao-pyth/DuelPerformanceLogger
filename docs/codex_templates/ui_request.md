# Codex Template: UI Request

Use this template when creating Codex tasks for UI-related work (KV updates, screen controllers, visual polish).

---

## Summary
- **Feature / Screen:**
- **Goal:**
- **Design Reference:** (link to spec e.g., `../specs/ui/MenuScreen.md`)

## Requirements
- [ ] KV files updated under `app/function/ui/kv/`
- [ ] Controller logic in `app/function/ui/screens/`
- [ ] Theme colors sourced from `ui/theme.py`
- [ ] Localization keys added to `strings.menu.*` (if applicable)
- [ ] Snapshot tests updated (`pytest -m snapshot`)

## Assets
- Mockups / screenshots:
- Icon or font updates:

## Acceptance Criteria
1. 
2. 
3. 

## Testing Commands
- `pytest -m snapshot`
- `python -m app.tools.kv_lint`

## Rollout / Notes
- Impacted release: `DPL.x.y.z`
- Feature flag / config toggle:
- Telemetry events to emit:

**Last Updated:** 2025-10-12
