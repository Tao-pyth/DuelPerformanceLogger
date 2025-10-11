"""Centralized filesystem path helpers for Duel Performance Logger."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from platform import system


_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_APP_ROOT = _PROJECT_ROOT / "app"
_PACKAGE_ROOT = _APP_ROOT / "function"
_RESOURCE_ROOT = _PROJECT_ROOT / "resource"


def project_root() -> Path:
    """Return the absolute path to the repository root."""

    return _PROJECT_ROOT


def app_root() -> Path:
    """Return the root directory for application source code."""

    return _APP_ROOT


def package_root() -> Path:
    """Return the ``app.function`` package root."""

    return _PACKAGE_ROOT


def resource_root() -> Path:
    """Return the root directory containing bundled read-only assets."""

    return _RESOURCE_ROOT


def resource_path(*parts: str) -> Path:
    """Join *parts* onto the resource root and return the resulting path."""

    return resource_root().joinpath(*parts)


def theme_path(*parts: str) -> Path:
    """Return a path within the theme resource directory."""

    return resource_path("theme", *parts)


def web_path(*parts: str) -> Path:
    """Return a path within the web (Eel) asset directory."""

    return resource_path("web", *parts)


@lru_cache(maxsize=1)
def user_data_root() -> Path:
    """Return the root directory for writable user data and ensure it exists."""

    platform_name = system()
    if platform_name == "Windows":
        base_dir = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif platform_name == "Darwin":
        base_dir = Path.home() / "Library" / "Application Support"
    else:
        base_dir = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))

    target = base_dir / "DuelPerformanceLogger"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _ensure_subdir(name: str) -> Path:
    path = user_data_root() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_dir() -> Path:
    """Directory that stores the SQLite database files."""

    return _ensure_subdir("db")


def log_dir() -> Path:
    """Directory that stores application log files."""

    return _ensure_subdir("logs")


def backup_dir() -> Path:
    """Directory that stores exported backup files."""

    return _ensure_subdir("backups")


def config_dir() -> Path:
    """Directory that stores user-modifiable configuration files."""

    return _ensure_subdir("config")


def config_path(filename: str = "config.conf") -> Path:
    """Return the writable configuration file path for *filename*."""

    return config_dir() / filename


def default_config_path() -> Path:
    """Return the packaged default configuration file path."""

    return theme_path("config.conf")


def strings_path() -> Path:
    """Return the packaged localized strings JSON file path."""

    return theme_path("json", "strings.json")


def web_root() -> Path:
    """Return the root directory containing bundled web assets."""

    return web_path()


__all__ = [
    "app_root",
    "backup_dir",
    "config_dir",
    "config_path",
    "database_dir",
    "default_config_path",
    "log_dir",
    "package_root",
    "project_root",
    "resource_path",
    "resource_root",
    "strings_path",
    "theme_path",
    "web_path",
    "web_root",
    "user_data_root",
]
