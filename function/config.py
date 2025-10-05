"""Application configuration management utilities."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, MutableMapping


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "resource" / "theme" / "config.json"


DEFAULT_CONFIG: dict[str, Any] = {
    "ui": {
        "mode": "normal",  # normal | broadcast
    },
    "database": {
        "expected_version": 3,
        "last_backup": "",
    },
}


def _ensure_directory() -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_config() -> dict[str, Any]:
    """Return the persisted configuration or the defaults when missing."""

    _ensure_directory()
    if not _CONFIG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)

    with _CONFIG_PATH.open("r", encoding="utf-8") as stream:
        try:
            data = json.load(stream)
        except json.JSONDecodeError:
            # 破損時は安全側で既定値を使用
            save_config(DEFAULT_CONFIG)
            return dict(DEFAULT_CONFIG)

    merged = dict(DEFAULT_CONFIG)
    _deep_update(merged, data)
    return merged


def save_config(config: MutableMapping[str, Any]) -> None:
    """Persist the given configuration mapping to disk."""

    _ensure_directory()
    with _CONFIG_PATH.open("w", encoding="utf-8") as stream:
        json.dump(config, stream, ensure_ascii=False, indent=2, sort_keys=True)


def _deep_update(base: MutableMapping[str, Any], updates: MutableMapping[str, Any]) -> None:
    for key, value in updates.items():
        if (
            key in base
            and isinstance(base[key], MutableMapping)
            and isinstance(value, MutableMapping)
        ):
            _deep_update(base[key], value)
        else:
            base[key] = value


def get_config_path() -> Path:
    """Expose the configuration path for informational purposes."""

    return _CONFIG_PATH

