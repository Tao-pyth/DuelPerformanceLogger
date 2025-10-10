# 00. Baseline Environment & Toolchain

Duel Performance Logger (DPL) targets Windows 10/11 desktop environments, packaged via PyInstaller in one-folder mode. This document codifies the supported platforms, toolchain requirements, and baseline assumptions for developers and CI.

## Supported Platforms

| Component | Version | Notes |
|-----------|---------|-------|
| OS | Windows 10 22H2 / Windows 11 23H2 | Primary execution environment |
| Python | 3.10.x (CPython) | Used for development and PyInstaller builds |
| Kivy | 2.3.x | UI framework |
| KivyMD | 1.1.x fork | Bundled with app resources |
| SQLite | 3.45+ | Embedded via Python stdlib |
| PyInstaller | 6.x | One-folder packaging |

## Development Dependencies

1. Install Python 3.10 and ensure `pip`, `venv`, and `wheel` are available.
2. Create a virtual environment: `python -m venv .venv`.
3. Activate the environment and install requirements: `pip install -r requirements.txt`.
4. Install Windows 10 SDK command-line tools for signing and resource inspection.
5. Configure `pyinstaller` path in `PATH` or invoke via module (`python -m PyInstaller`).

## Fonts and Localization

- Bundle `mgenplus-1p-regular.ttf` and `mgenplus-1p-bold.ttf` inside `resource/fonts/`.
- Register fonts at runtime via `app/function/ui/fonts.py`; migrations ensure registration entries exist.
- Verify Japanese UI strings using Windows IME before release.

## Storage Layout

- Install directory: `%PROGRAMFILES%/DuelPerformanceLogger/` (one-folder).
- Writable data: `%APPDATA%/DuelPerformanceLogger/` for config, DSL, and SQLite DB.
- Logs: `%LOCALAPPDATA%/DuelPerformanceLogger/logs/app.log`.

## Updater Integration

- `Updater.exe` ships alongside `Main.exe` within the one-folder output.
- Updates are executed from `%TEMP%/DPL_Update_*` to allow self-replacement.
- Command-line contract is versioned (`v1`) and must remain backward compatible.

## CI Expectations

- GitHub Actions workflow `windows-build.yml` provisions Python 3.10.
- Cache `.venv` or `pip` packages via `actions/cache` keyed by `requirements.txt` hash.
- Produce artifact `DuelPerformanceLogger-<version>-win64.zip` containing the one-folder build.
- Publish release notes referencing `[08_release](08_release.md)`.

## Security Baseline

- Enforce TLS 1.2+ for update downloads.
- Validate SHA256 signatures against values published in release notes.
- Store signing certificates in Azure Key Vault; pipeline retrieves via OIDC.

## Checklist

- [ ] Python 3.10.x installed and active.
- [ ] Requirements installed from lock-approved sources.
- [ ] Fonts validated with Japanese UI.
- [ ] CI artifacts include both `Main.exe` and `Updater.exe`.

**Last Updated:** 2025-10-12
