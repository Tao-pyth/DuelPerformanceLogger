"""Application configuration management utilities."""

from __future__ import annotations

import configparser
from pathlib import Path
from typing import Any, MutableMapping


_CONFIG_PATH = Path(__file__).resolve().parent.parent / "resource" / "theme" / "config.conf"


DEFAULT_CONFIG: dict[str, Any] = {
    "database": {
        "expected_version": 3,
    },
}


def load_config() -> dict[str, Any]:
    """Return the persisted configuration or the defaults when missing."""

    parser = configparser.ConfigParser()
    if _CONFIG_PATH.exists():
        parser.read(_CONFIG_PATH, encoding="utf-8")

    config = _configparser_to_dict(parser)
    merged = dict(DEFAULT_CONFIG)
    _deep_update(merged, config)
    return merged


def _configparser_to_dict(parser: configparser.ConfigParser) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for section in parser.sections():
        items = {}
        for key, value in parser.items(section):
            items[key] = value
        data[section] = items
    return data


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

