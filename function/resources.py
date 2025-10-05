"""Utility helpers for loading localized resources from JSON files."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


# 文字列リソースが格納されているディレクトリを事前に解決しておく。
_RESOURCE_DIR = Path(__file__).resolve().parent.parent / "resource" / "json"


@lru_cache(maxsize=1)
def _load_strings() -> dict[str, Any]:
    """Load and cache the string resources from disk."""

    strings_path = _RESOURCE_DIR / "strings.json"
    with strings_path.open(encoding="utf-8") as stream:
        return json.load(stream)


def get_text(path: str, default: Any | None = None) -> Any:
    """Retrieve a value from the string resources by dotted path."""

    data: Any = _load_strings()
    for segment in path.split("."):
        if isinstance(data, dict) and segment in data:
            data = data[segment]
        else:
            return default if default is not None else path
    return data
