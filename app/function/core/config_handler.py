"""Helpers for persisting UI recording settings to ``app_settings.json``."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from . import paths

__all__ = [
    "DEFAULT_APP_SETTINGS",
    "RecordingSettings",
    "load_app_settings",
    "save_app_settings",
    "load_recording_settings",
    "update_recording_settings",
]


_LOGGER = logging.getLogger(__name__)

DEFAULT_APP_SETTINGS: dict[str, Any] = {
    "recording": {
        "save_directory": str(paths.recording_output_dir()),
        "bitrate": "6000k",
        "audio_bitrate": "160k",
        "fps": 60,
        "profile": "16:9",
        "ffmpeg_path": "",
        "auto_download_ffmpeg": False,
        "audio_device": "",
        "video_source": "desktop",
    }
}


@dataclass(slots=True)
class RecordingSettings:
    """Normalized representation of recording configuration values."""

    save_directory: Path
    bitrate: str
    audio_bitrate: str
    fps: int
    profile: str
    ffmpeg_path: Path | None
    auto_download_ffmpeg: bool
    audio_device: str | None
    video_source: str

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "RecordingSettings":
        data = dict(DEFAULT_APP_SETTINGS["recording"])
        data.update({k: mapping.get(k, v) for k, v in data.items()})
        save_directory = Path(str(mapping.get("save_directory", data["save_directory"])))
        ffmpeg_raw = str(mapping.get("ffmpeg_path", data["ffmpeg_path"]) or "").strip()
        ffmpeg_path = Path(ffmpeg_raw).expanduser() if ffmpeg_raw else None
        audio_device = mapping.get("audio_device") or None
        video_source = str(mapping.get("video_source", data["video_source"]) or "desktop")
        settings = cls(
            save_directory=save_directory,
            bitrate=str(mapping.get("bitrate", data["bitrate"])),
            audio_bitrate=str(mapping.get("audio_bitrate", data["audio_bitrate"])),
            fps=int(mapping.get("fps", data["fps"])),
            profile=str(mapping.get("profile", data["profile"])),
            ffmpeg_path=ffmpeg_path,
            auto_download_ffmpeg=bool(
                mapping.get("auto_download_ffmpeg", data["auto_download_ffmpeg"])
            ),
            audio_device=audio_device,
            video_source=video_source,
        )
        settings.ensure_directories()
        return settings

    def ensure_directories(self) -> None:
        """Guarantee that the configured save directory exists."""

        try:
            self.save_directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:  # pragma: no cover - filesystem guard
            _LOGGER.warning("Failed to create recording directory", exc_info=exc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "save_directory": str(self.save_directory),
            "bitrate": self.bitrate,
            "audio_bitrate": self.audio_bitrate,
            "fps": self.fps,
            "profile": self.profile,
            "ffmpeg_path": str(self.ffmpeg_path) if self.ffmpeg_path else "",
            "auto_download_ffmpeg": self.auto_download_ffmpeg,
            "audio_device": self.audio_device or "",
            "video_source": self.video_source,
        }


def _deep_update(base: MutableMapping[str, Any], updates: Mapping[str, Any]) -> None:
    for key, value in updates.items():
        if (
            key in base
            and isinstance(base[key], MutableMapping)
            and isinstance(value, Mapping)
        ):
            _deep_update(base[key], value)
        else:
            base[key] = value


def load_app_settings(path: Path | None = None) -> dict[str, Any]:
    """Load `app_settings.json`, merging it with :data:`DEFAULT_APP_SETTINGS`."""

    target = path or paths.app_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    merged: dict[str, Any] = json.loads(json.dumps(DEFAULT_APP_SETTINGS))
    if target.exists():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            _LOGGER.warning("Invalid app_settings.json detected; ignoring", exc_info=exc)
        else:
            if isinstance(payload, Mapping):
                _deep_update(merged, payload)
    return merged


def save_app_settings(settings: Mapping[str, Any], path: Path | None = None) -> None:
    """Persist *settings* to `app_settings.json`."""

    target = path or paths.app_settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(settings, ensure_ascii=False, indent=2, sort_keys=True)
    target.write_text(serialized + "\n", encoding="utf-8")


def load_recording_settings(path: Path | None = None) -> RecordingSettings:
    """Return :class:`RecordingSettings` loaded from persisted JSON."""

    settings = load_app_settings(path)
    recording = settings.get("recording", {})
    if not isinstance(recording, Mapping):
        recording = {}
    return RecordingSettings.from_mapping(recording)


def update_recording_settings(
    settings: RecordingSettings,
    root: MutableMapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Return *root* merged with the provided :class:`RecordingSettings`."""

    container: dict[str, Any] = {}
    _deep_update(container, root or DEFAULT_APP_SETTINGS)
    container.setdefault("recording", {})
    if isinstance(container["recording"], MutableMapping):
        container["recording"].update(settings.to_dict())
    else:
        container["recording"] = settings.to_dict()
    return container
