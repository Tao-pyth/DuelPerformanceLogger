# UI Spec: MenuScreen

This specification captures the UX and technical requirements for `MenuScreen`, the primary entry point of Duel Performance Logger.

## Overview

- Purpose: Provide quick access to duel logs, performance dashboards, and updater actions.
- Controller: `app/function/ui/screens/menu_screen.py`
- KV Layout: `app/function/ui/kv/menu_screen.kv`
- Dependencies: `ui.widgets.performance_card`, `core.updater`, `core.telemetry`

## Layout Structure

| Section | Description | Components |
|---------|-------------|------------|
| Header | Displays logo and version (`__version__`) | `LogoWidget`, `VersionLabel` |
| Quick Actions | Buttons for `Start Duel Log`, `View Analytics`, `Check Updates` | `MDRectangleFlatButton` x3 |
| Recent Activity | List of last 5 duels with status badges | `RecycleView` |
| Footer | Links to settings, docs, and support | `FooterBar` |

### Wireframe

```
+--------------------------------------------------------+
| Logo      Duel Performance Logger       vDPL.1.4.0     |
+--------------------------------------------------------+
| [ Start Duel Log ] [ View Analytics ] [ Check Updates ] |
|                                                        |
| Recent Activity                                        |
|  ----------------------------------------------------  |
| | Duel vs. Kaiba     | Result: Win | Rating: +12    | |
| | ...                                               | |
|  ----------------------------------------------------  |
|                                                        |
| Settings | Docs | Support                              |
+--------------------------------------------------------+
```

## Behavior

- `Start Duel Log`: Navigates to `LogSetupScreen`.
- `View Analytics`: Opens `AnalyticsScreen` with cached summaries.
- `Check Updates`: Calls `core.updater.schedule_update()` after download confirmation dialog.
- Header version label updates dynamically based on `core.version.__version__`.
- Recent activity auto-refreshes via async task every 60 seconds.

## State & Data

- Uses `ui.state.AppState.recent_duels` (list of dict) with keys `opponent`, `result`, `rating_delta`, `timestamp`.
- When no data exists, show placeholder card with guidance to start logging.

## Telemetry

| Event | Trigger | Payload |
|-------|---------|---------|
| `menu_action` | Quick action button tap | `{ "action": "start_duel" | "analytics" | "check_update" }` |
| `menu_impression` | Screen enter | `{ "duel_count": len(recent_duels) }` |

## Accessibility & Localization

- Buttons include `accessibility_text` matching localized strings.
- Support keyboard navigation (Tab order: Start → Analytics → Updates → Settings → Docs → Support).
- All labels sourced from `strings.menu.*`.

## Validation Checklist

- [ ] Version label matches `__version__` during runtime.
- [ ] Update dialog respects async policy and shows progress overlay.
- [ ] Telemetry events emitted on button tap.
- [ ] Placeholder displayed when `recent_duels` empty.
- [ ] Localization covers ja-JP and en-US.

**Last Updated:** 2025-10-12
