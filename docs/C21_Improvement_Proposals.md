# C21. Improvement Proposals
This catalogue describes potential enhancement tracks for the Duel Performance Logger UI stack. Each proposal includes background context, action items, and acceptance criteria that can be handled in dedicated pull requests.

## Table of Contents
- [1. Guard KV Loading Order](#proposal-1)
- [2. KV/Python Class Consistency Check](#proposal-2)
- [3. Headless KV Smoke Test](#proposal-3)
- [4. Introduce Style Tokens](#proposal-4)
- [5. Standardise Shared Components](#proposal-5)
- [6. Form Validation Mixin](#proposal-6)
- [7. Keyboard Focus Improvements](#proposal-7)
- [8. Internationalisation Enforcement](#proposal-8)
- [9. Screen Creation Tests](#proposal-9)
- [10. Developer Documentation Refresh](#proposal-10)

## <a id="proposal-1"></a>1. Guard KV Loading Order
**Background**: `resource_add_path(...)` must run before `Builder.load_file(app.kv)`. Mistakes cause runtime errors that are hard to diagnose.

**Tasks**
- Add a code comment in `main.py` clarifying the required call order.
- Wrap the loader in a helper that enforces the sequence programmatically.
- Document the rule in the README.

**Acceptance Criteria**
- Startup path always executes the correct order.
- Comment and README clearly describe the requirement.

## <a id="proposal-2"></a>2. KV/Python Class Consistency Check
**Background**: Divergence between `<FooScreen>:` in KV files and `class FooScreen(MDScreen)` definitions leads to runtime failures.

**Tasks**
- Add a script to extract `<ClassName>:` from `screens/*.kv`.
- Parse `class .*Screen` from `function/screen/*.py`.
- Fail CI when discrepancies occur.

**Acceptance Criteria**
- CI reports mismatches.
- Current codebase passes the check.

## <a id="proposal-3"></a>3. Headless KV Smoke Test
**Background**: Syntax regressions in KV files should surface quickly.

**Tasks**
- Execute `Builder.load_file("resource/theme/gui/app.kv")` once in CI.
- Fail the job if parsing raises an exception.

**Acceptance Criteria**
- Windows and Ubuntu CI runs stay green.
- KV parsing errors surface immediately.

## <a id="proposal-4"></a>4. Introduce Style Tokens
**Background**: Spacing, typography, radii, and colour usage differ across screens.

**Tasks**
- Define spacing tokens (e.g., `#:set GAP_S/M/L`) in `styles/Spacing.kv`.
- Define typography presets in `styles/Typography.kv`.
- Apply tokens in at least one representative screen.

**Acceptance Criteria**
- Token files exist and are referenced.
- Updating a token cascades through the applied screen.

## <a id="proposal-5"></a>5. Standardise Shared Components
**Background**: Toolbars, dialogs, and buttons are duplicated across screens.

**Tasks**
- Create shared definitions under `components/`.
- Replace duplicates in two to three screens.
- Document usage patterns in README snippets or inline comments.

**Acceptance Criteria**
- Shared components are reused across multiple screens.
- New screens can adopt the common components easily.

## <a id="proposal-6"></a>6. Form Validation Mixin
**Background**: Save-button enablement logic varies per screen.

**Tasks**
- Implement a `FormValidationMixin` that tracks field state and exposes `can_save()`.
- Update KV bindings to toggle `btn_save.disabled = not root.can_save()`.
- Apply the mixin to a representative screen.

**Acceptance Criteria**
- Save buttons remain disabled until required inputs are valid.
- Logic is shareable with other screens.

## <a id="proposal-7"></a>7. Keyboard Focus Improvements
**Background**: Keyboard navigation lacks consistency.

**Tasks**
- Set `focus=True` on the first field within `on_pre_enter`.
- Tune tab order via KV ordering or explicit `tab_width` values.
- Add shortcuts (Enter to save, Esc to cancel) suitable for Windows users.

**Acceptance Criteria**
- Representative screen supports full keyboard-driven workflows.
- Initial focus lands on the correct field.

## <a id="proposal-8"></a>8. Internationalisation Enforcement
**Background**: Hard-coded strings bypass the translation pipeline.

**Tasks**
- Replace KV literals with `get_text("...")` where possible.
- Add a script to flag hard-coded `text:` entries in KV files.
- Verify `strings.json` integrity during CI.

**Acceptance Criteria**
- Representative screen retrieves UI text via `strings.json`.
- CI detects missing translations or unused keys.

## <a id="proposal-9"></a>9. Screen Creation Tests
**Background**: Screen imports and bindings can silently break.

**Tasks**
- Add `pytest` coverage that performs `build → add → remove` for target screens.
- Assert that critical `ids` exist.
- Optionally verify `can_save()` behaviour in one case.

**Acceptance Criteria**
- CI includes the new tests and passes.
- Baseline screen behaviour is validated automatically.

## <a id="proposal-10"></a>10. Developer Documentation Refresh
**Background**: Contributors need clearer onboarding material.

**Tasks**
- Document the screen creation flow (Python class + `screens/<ClassName>.kv` + ScreenManager registration).
- Explain include ordering, token usage, and component imports.
- Add troubleshooting guidance for KV parse failures, class mismatches, and resource path issues.

**Acceptance Criteria**
- README and related docs guide developers through adding a screen.
- Common error scenarios include actionable remediation steps.

**Last Updated:** 2025-10-12
