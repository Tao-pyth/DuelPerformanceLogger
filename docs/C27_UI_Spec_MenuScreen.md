# C27. UI Spec: MenuScreen
This specification captures the UX and technical requirements for `MenuScreen`, the primary entry point of Duel Performance Logger.

## Table of Contents
- [Overview](#overview)
- [Layout Structure](#layout-structure)
- [Wireframe](#wireframe)
- [Behavior](#behavior)
- [State & Data](#state-data)
- [Telemetry](#telemetry)
- [Accessibility & Localization](#accessibility)
- [Validation Checklist](#validation-checklist)

## <a id="overview"></a>Overview
- Purpose: Provide quick access to duel logs, performance dashboards, and updater actions.
- Controller: `app/function/ui/screens/menu_screen.py`
- KV Layout: `app/function/ui/kv/menu_screen.kv`
- Dependencies: `ui.widgets.performance_card`, `core.updater`, `core.telemetry`

## <a id="layout-structure"></a>Layout Structure
| Section | Description | Components |
|---------|-------------|------------|
| Header | Displays logo and version (`__version__`) | `LogoWidget`, `VersionLabel` |
| Quick Actions | Buttons for `Start Duel Log`, `View Analytics`, `Check Updates` | `MDRectangleFlatButton` ×3 |
| Recent Activity | List of last 5 duels with status badges | `RecycleView` |
| Footer | Links to settings, docs, and support | `FooterBar` |

## <a id="wireframe"></a>Wireframe
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

## <a id="behavior"></a>Behavior
- `Start Duel Log`: Navigates to `LogSetupScreen`.
- `View Analytics`: Opens `AnalyticsScreen` with cached summaries.
- `Check Updates`: Calls `core.updater.schedule_update()` after download confirmation dialog.
- Header version label updates dynamically based on `core.version.__version__`.
- Recent activity auto-refreshes via async task every 60 seconds.

## <a id="state-data"></a>State & Data
- Uses `ui.state.AppState.recent_duels` (list of dict) with keys `opponent`, `result`, `rating_delta`, `timestamp`.
- When no data exists, show a placeholder card with guidance to start logging.

## <a id="telemetry"></a>Telemetry
| Event | Trigger | Payload |
|-------|---------|---------|
| `menu_action` | Quick action button tap | `{ "action": "start_duel" | "analytics" | "check_update" }` |
| `menu_impression` | Screen enter | `{ "duel_count": len(recent_duels) }` |

## <a id="accessibility"></a>Accessibility & Localization
- Buttons include `accessibility_text` matching localized strings.
- Support keyboard navigation (Tab order: Start → Analytics → Updates → Settings → Docs → Support).
- Source all labels from `strings.menu.*`.

## <a id="validation-checklist"></a>Validation Checklist
- [ ] Version label matches `__version__` during runtime.
- [ ] Update dialog respects async policy and shows progress overlay.
- [ ] Telemetry events emitted on button tap.
- [ ] Placeholder displayed when `recent_duels` is empty.
- [ ] Localisation covers ja-JP and en-US.

**Last Updated:** 2025-10-12
