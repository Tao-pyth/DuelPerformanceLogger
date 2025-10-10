# 02. KV & UI Layout Guidelines

This guide defines the conventions for Kivy/KivyMD KV files and screen implementations within Duel Performance Logger.

## File Organization

- KV files reside under `app/function/ui/kv/` and mirror their Python controller names (e.g., `menu_screen.py` → `menu_screen.kv`).
- Screens inherit from `MDScreen` and register in `app/function/ui/router.py`.
- Reusable components live in `app/function/ui/widgets/` with matching KV partials.

## Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Screen classes | `PascalCaseScreen` | `MenuScreen` |
| KV ids | `snake_case` | `start_button` |
| Properties | `snake_case` | `progress_ratio` |
| Translations | `strings.<context>.<key>` | `strings.menu.start` |

## Styling Rules

- Use theme palettes defined in `ui/theme.py`; do not hardcode colors.
- Font families reference registered names (`"MgenPlus"`).
- Default spacing units: `dp(12)` for padding, `dp(8)` for spacing, unless UX specifies otherwise.
- Responsive layouts must adapt to widths from 1024px to 1920px.

## Binding & Logic

1. Keep business logic in Python controllers; KV should only declare bindings.
2. Use `@mainthread` decorators for UI updates triggered from async tasks.
3. `Updater` progress is surfaced via `ProgressOverlay`; update values through `ui.events.bus`.
4. Use `ui.state.AppState` for cross-screen data. Avoid global variables.

## Accessibility

- Provide `accessibility_text` for actionable widgets where supported.
- Ensure contrast ratio meets WCAG AA (> 4.5:1) on default themes.
- For keyboard navigation, map `on_key_down` handlers to focus the next widget.

## Testing

- Snapshot tests reside in `tests/ui/test_screens.py` and rely on screen factory fixtures.
- Add new screens to the snapshot registry with expected widget tree counts.
- Validate KV syntax using `python -m app.tools.kv_lint`.

## Checklist

- [ ] KV filename matches controller module.
- [ ] Theme colors sourced from `ui/theme.py`.
- [ ] Async callbacks marshal to main thread.
- [ ] Snapshot tests updated.

**Last Updated:** 2025-10-12
