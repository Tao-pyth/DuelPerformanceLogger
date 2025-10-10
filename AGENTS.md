# AGENT CODING GUIDELINES (Duel Performance Logger)

This document defines the agent coding and operational rules for all contributors and automation tools (Codex, CI, etc.)
in the Duel Performance Logger (DPL) project.

---

## 1. General Principles

- Follow the **semantic versioning** scheme `DPL.<MAJOR>.<MINOR>.<PATCH>`:
  - **MAJOR** — Breaking changes (DB/DSL incompatibility, destructive schema change)
  - **MINOR** — Backward-compatible additions (new columns, new DSL keys)
  - **PATCH** — Bug fixes and non-breaking adjustments
- Never wrap import statements in `try/except` blocks.
- Follow the instructions and conventions in any `AGENTS.md` within the relevant directory tree.
- After code edits, always:
  1. Run relevant tests.
  2. Record migration results if applicable.
  3. Include version and schema changes in the changelog.

---

## 2. Directory and Build Structure

- Source code resides under `app/`.
- Read-only assets reside under `resources/` and are bundled into the PyInstaller package.
- User-generated and writable data (DB, DSL, logs, config) is stored in:%APPDATA%/DuelPerformanceLogger/
- All path references **must** go through `app/function/core/paths.py`.
- The PyInstaller spec file lives in `scripts/pyinstaller/duel_logger.spec`.
- Exe packaging uses the **onefolder** mode; `Updater.exe` is included alongside the main build.

---

## 3. Update / Deployment Policy

- **Main.exe must never self-overwrite.**
- Application updates are handled via a separate `Updater.exe` process:
1. `Main.exe` downloads and unpacks the new version to a staging folder.
2. Launch `Updater.exe` from a temp directory with the following parameters:
   ```
   --install "<INSTALL_DIR>" --staging "<STAGING_DIR>" --main-name "Main.exe"
   --args "--via-updater --updated-from=<old> --updated-to=<new>"
   ```
3. `Updater.exe` waits for `Main.exe` to exit, replaces files atomically, and restarts the app.
- `Updater.exe` has a **stable CLI interface (v1)** and can be **packaged once** within the build.
- Always execute Updater from a temp folder to allow its own replacement during update.

---

## 4. Migration Rules

- Upon startup, if `config["app_version"] != __version__`, run the migration chain:
1. Backup DB and DSL data.
2. Apply `migrations.py` (DDL and config key updates).
3. Update schema version in `schema_version` table.
4. Write new `app_version` to config.
- All migrations must be **idempotent** and logged under `logs/app.log`.
- Migrations handle:
- DB (ALTER TABLE, CREATE TABLE, indexes)
- Config (key addition, renaming)
- DSL (YAML key completion)

---

## 5. Version and Release Handling

- The canonical version is defined in `app/function/core/version.py` as `__version__`.
- Tag naming on GitHub must match the app version, e.g., `DPL.1.2.0`.
- GitHub Releases are used for distribution; executables are not committed to the repository.
- Release packaging steps:
1. Update `__version__`.
2. Build with PyInstaller.
3. Verify migrations.
4. Zip onefolder build and attach to GitHub Releases.
- Exe signatures or SHA256 hashes must be provided alongside builds for verification.

---

## 6. Testing and Verification

- Always run migration tests before tagging a release.
- Verify:
- Kivy/KivyMD screens load successfully (KV integrity).
- Japanese font registration (mgenplus) succeeds.
- DB and config migration logs show correct version increments.
- Updater.exe can perform a replace-and-relaunch cycle on Windows 10/11.
- Tests must pass under the current Python baseline (3.10.x).

---

## 7. Logging and Error Policy

- Log files: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log`
- Use structured logging (`[LEVEL] message`) for:
- Migration steps
- Updater actions
- Critical errors
- Do not suppress exceptions silently. Propagate and log them with context.

---

## 8. CI / Automation Notes

- GitHub Actions handle build and release automation:
- On `tag push`, trigger PyInstaller build and asset upload to GitHub Releases.
- Automated agents (e.g., Codex) must:
- Respect this document’s versioning and migration structure.
- Avoid editing paths or resource directories directly.
- Generate code assuming PyInstaller onefolder mode.

---

## 9. Security / Integrity

- Always verify hashes for downloaded update packages before replacing.
- Do not execute unknown binaries within the update flow.
- Keep `Updater.exe` minimal and auditable.

---

## 10. References

- `/docs/00_baseline.md` — environment and dependency baseline  
- `/docs/04_async_policy.md` — asynchronous and progress behavior  
- `/docs/08_release.md` — release management  
- `/scripts/pyinstaller/duel_logger.spec` — packaging specification  

---

**Last Updated:** 2025-10-10  
**Maintainer:** DPL Development Team
