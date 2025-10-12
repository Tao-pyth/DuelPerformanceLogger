# C28. Duel Performance Logger Wiki Overview
This page summarises the current architecture, assets, and next steps for the Duel Performance Logger desktop application.

## Table of Contents
- [Project Snapshot](#project-snapshot)
- [Application Architecture](#application-architecture)
  - [UI and State Management](#ui-state-management)
  - [Localization Resources](#localization-resources)
  - [Configuration Management](#configuration-management)
  - [Database Layer](#database-layer)
  - [Logging](#logging)
- [Data Flow Overview](#data-flow)
- [Existing Assets](#existing-assets)
- [Developer Notes](#developer-notes)
- [Next Documentation Steps](#next-steps)
- [Incident Response](#incident-response)

## <a id="project-snapshot"></a>Project Snapshot
- **Purpose:** Provide a Windows desktop UI (Python + Eel) for recording duel outcomes, analysing performance, and guiding deck improvements.
- **Current Focus:** Stabilise deck/season/match logging, database backups, and UI display modes.
- **Status:** UI components live under `resource/web/`, localisation strings reside in `resource/theme/json/`, and runtime state is exposed through `main.py` APIs such as `fetch_snapshot`.

## <a id="application-architecture"></a>Application Architecture
### <a id="ui-state-management"></a>UI and State Management
- `main.py` boots Eel and exposes `fetch_snapshot` so the front end can poll the latest `AppState`.
- `function.cmn_app_state.AppState` stores decks, seasons, matches, and database handles.
- The front end (`resource/web/static/js/app.js`) updates the DOM and consumes Eel-exposed functions like `show_notification`.
- Shared styling lives in `resource/web/static/css/` via CSS variables, with `resource/web/index.html` as the root template.

### <a id="localization-resources"></a>Localization Resources
- `function.cmn_resources.get_text` reads `resource/theme/json/strings.json` using dot-separated keys and caches results via `lru_cache`.
- Strings cover UI menus, toasts, dialogs, and remain Japanese-first with English glosses when necessary.

### <a id="configuration-management"></a>Configuration Management
- `function.cmn_config` reads `resource/theme/config.conf`, merging against `DEFAULT_CONFIG` using `configparser`.
- Runtime mode flags reside in the database metadata, leaving static expectations (e.g., schema version) in the config file.

### <a id="database-layer"></a>Database Layer
- `function.cmn_database.DatabaseManager` wraps SQLite3 with automatic directory creation, foreign-key enforcement, and `sqlite3.Row` conversion.
- `initialize_database` allows idempotent table creation, while `ensure_database` validates metadata before use.
- Schema overview:
  - `decks`: Deck names and descriptions.
  - `seasons`: Seasonal windows and metadata.
  - `matches`: Results, opponent deck, keywords, timestamps, and scores.
  - `db_metadata`: Schema version, migrations, and integrity markers.
- Domain-specific exceptions (`DatabaseError`, `DuplicateEntryError`) surface meaningful errors to the UI layer.

### <a id="logging"></a>Logging
- `function.cmn_logger.log_error` writes timestamped entries to `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log`, capturing stack traces and context fields.

## <a id="data-flow"></a>Data Flow Overview
1. UI actions create or edit decks and seasons through `DatabaseManager`, storing records in SQLite.
2. Match-entry screens persist duel data and echo updates back to the UI for confirmation.
3. Settings view offers CSV backups and database reset workflows with user notifications.
4. Errors log via `log_error` and present localised UI messages.

## <a id="existing-assets"></a>Existing Assets
- `resource/theme/json/strings.json`: Localisation catalogue.
- `resource/theme/config.conf`: Default configuration (read-only).
- `resource/web/`: HTML, CSS, and JavaScript assets.
- `resource/db/`: SQLite storage directory (tracked with `.gitkeep`).
- `resource/log/`: Default log directory for development builds.

## <a id="developer-notes"></a>Developer Notes
- Install the Python runtime and Chromium/Edge WebView2 to develop with Eel. `requirements.txt` pins the supported versions.
- Invoke `DatabaseManager.ensure_database()` before launching the UI to guarantee schema alignment.
- When packaging with PyInstaller, rely on `Path.resolve()` helpers to keep asset paths valid inside the one-folder layout.

## <a id="next-steps"></a>Next Documentation Steps
- Add annotated screenshots and UI flow diagrams for each major screen.
- Publish an entity-relationship diagram and migration history for the database.
- Document unit, integration, and snapshot testing strategies.

## <a id="incident-response"></a>Incident Response
- Capture support bundles with `tools/support/package_logs.ps1` and attach them to Jira tickets.
- Document mitigation and follow-up tasks here and in release-specific notes.

**Last Updated:** 2025-10-12
