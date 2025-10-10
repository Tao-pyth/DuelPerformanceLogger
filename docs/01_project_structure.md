# 01. Project Structure & Ownership

This document describes the top-level layout of the Duel Performance Logger repository, including ownership boundaries and packaging considerations for the PyInstaller one-folder build.

## Directory Overview

| Path | Owner | Description |
|------|-------|-------------|
| `app/` | Core Engineering | Application source code (Python/Kivy). |
| `app/function/core/` | Core Engineering | Core services: paths, config, migrations, versioning. |
| `app/function/ui/` | UI Team | Screen controllers, widgets, and KV integration. |
| `app/resource/` | Core + UI | Runtime assets bundled into build. |
| `resource/` | Content Team | Static fonts, icons, localization files. |
| `docs/` | Documentation Team | Authoritative policy and process manuals. |
| `scripts/pyinstaller/` | Build & Release | PyInstaller spec and packaging scripts. |
| `.github/workflows/` | DevOps | CI pipeline definitions. |

## Packaging Layout

The PyInstaller one-folder output is structured as follows:

```
DuelPerformanceLogger/
├── Main.exe
├── Updater.exe
├── app/  (Python modules)
├── resource/  (bundled assets)
└── vcruntime140.dll ...
```

- `Main.exe` is the PyInstaller bootstrap that launches the Kivy application.
- `Updater.exe` is copied into the same folder but executed from `%TEMP%` during updates.
- All Python modules are zipped within `app/` by PyInstaller but retain importable paths via `sys._MEIPASS`.

## Data Ownership

- User data lives in `%APPDATA%/DuelPerformanceLogger/` and includes `config.json`, `dsl/`, and `db/dpl.sqlite`.
- Migration scripts in `app/function/core/migrations/` are the single source of truth for schema evolution.
- Logs flow to `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log` via `app/function/core/logging.py`.

## Interface Contracts

- `app/function/core/paths.py` abstracts filesystem locations. Any new modules must consume these helpers.
- KV files under `app/function/ui/kv/` are loaded by name in `app/function/ui/loader.py`; follow naming `*.kv` mirroring screen classes.
- Updater CLI contract is detailed in `[05_error_taxonomy](05_error_taxonomy.md)` and `[08_release](08_release.md)`.

## Dependency Boundaries

- Core modules must not import UI packages to keep headless testing viable.
- UI modules may import core services but should communicate via defined interfaces (`service_*` modules).
- External integrations (REST, telemetry) live under `app/function/integration/` and must expose async-friendly APIs.

## Checklist

- [ ] New modules registered in `__all__` if required for packaging.
- [ ] KV files follow screen naming conventions.
- [ ] Paths resolved exclusively via `core.paths` helpers.
- [ ] Updater references keep CLI version in sync.

**Last Updated:** 2025-10-12
