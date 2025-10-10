# 03. Core ICD (Interface Control Document)

The Core Interface Control Document defines the contracts between Duel Performance Logger subsystems, focusing on configuration, migrations, telemetry, and the updater integration.

## Module Interfaces

| Module | Provides | Consumes | Notes |
|--------|----------|----------|-------|
| `core.paths` | `get_app_dir()`, `get_config_path()`, `get_db_path()` | `os`, `platform` | Must be the only source of filesystem paths. |
| `core.config` | `load_config()`, `save_config()`, schema versioning | `core.paths`, `core.migrations` | Saves JSON with `app_version`. |
| `core.migrations.runner` | `run_migrations(from_version, to_version)` | `core.config`, `core.db` | Logs events to `app.log`. |
| `core.db` | SQLite connection pool, query helpers | `core.paths` | Exposes context managers for transactions. |
| `core.version` | `__version__` constant, `parse_version()` | None | Serves as canonical version. |
| `core.updater` | `schedule_update(package_path, target_version)` | `subprocess`, `core.paths`, `core.version` | Launches `Updater.exe` from `%TEMP%`. |

## Configuration Schema

```json
{
  "app_version": "DPL.1.4.0",
  "language": "ja-JP",
  "telemetry_opt_in": true,
  "last_migration": "2025-09-30T12:00:00Z"
}
```

- `app_version` is compared against `core.version.__version__` at startup.
- `last_migration` is ISO8601 with Zulu timezone.
- Additional keys must have defaults defined in `core.config.DEFAULTS`.

## Migration Flow

1. Load configuration and compare versions.
2. When versions differ, backup DB and DSL directories to `%APPDATA%/DuelPerformanceLogger/backups/<timestamp>/`.
3. Execute SQL migrations via `core.migrations.sql` modules, applying in ascending order.
4. Apply DSL migrations using YAML patch scripts in `core.migrations.dsl`.
5. Update config defaults and bump `app_version`.
6. Log success and emit telemetry event `migration_completed` with duration.

## Updater Contract

- `core.updater.schedule_update()` prepares staging under `%TEMP%/DPL_Update_<uuid>`.
- The function invokes `Updater.exe` with parameters:

```
Updater.exe \
  --install "<install_dir>" \
  --staging "<staging_dir>" \
  --main-name "Main.exe" \
  --args "--via-updater --updated-from=<old> --updated-to=<new>"
```

- `Updater.exe` returns exit codes:
  - `0` success
  - `10` validation failure (hash mismatch)
  - `20` permission denied
  - `30` rollback performed

## Telemetry Events

| Event | Trigger | Payload |
|-------|---------|---------|
| `app_started` | Startup after migrations | `{ "version": __version__, "channel": build_channel }` |
| `migration_completed` | Successful migration | `{ "from": old, "to": new, "duration_ms": int }` |
| `update_download_failed` | HTTP error during download | `{ "status": code, "url": source }` |

Telemetry dispatch uses `core.telemetry.queue` and must be non-blocking.

## Checklist

- [ ] New config keys include defaults and migration entries.
- [ ] Updater exit codes handled via `core.errors.UpdaterError` mapping.
- [ ] Telemetry payloads respect schema documented here.
- [ ] Backups verified before destructive migrations.

**Last Updated:** 2025-10-12
