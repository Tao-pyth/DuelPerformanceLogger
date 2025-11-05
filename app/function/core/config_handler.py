"""Helpers for persisting UI recording settings to ``app_settings.json``."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, MutableMapping

from . import paths
from .ffmpeg_command_builder import QUALITY_PRESETS, resolve_quality_preset

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
        "save_directory": str(paths.recording_dir()),
        "quality_preset": "standard",
        "bitrate": QUALITY_PRESETS["standard"].video_bitrate,
        "audio_bitrate": QUALITY_PRESETS["standard"].audio_bitrate,
        "fps": QUALITY_PRESETS["standard"].fps,
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
    quality_preset: str
    bitrate: str
    audio_bitrate: str
    fps: int
    profile: str
    ffmpeg_path: Path | None
    auto_download_ffmpeg: bool
    audio_device: str | None
    video_source: str

    @classmethod
    def from_mapping(
        cls, mapping: Mapping[str, Any], *, prefer_explicit: bool = False
    ) -> "RecordingSettings":
        data = dict(DEFAULT_APP_SETTINGS["recording"])
        data.update({k: mapping.get(k, v) for k, v in data.items()})
        save_directory = Path(str(mapping.get("save_directory", data["save_directory"])))
        quality_name = str(mapping.get("quality_preset", "") or "").strip()
        if quality_name and not prefer_explicit:
            preset = QUALITY_PRESETS.get(quality_name.lower())
            if preset is not None:
                bitrate = str(mapping.get("bitrate", "")).strip().lower()
                audio_bitrate = str(mapping.get("audio_bitrate", "")).strip().lower()
                fps_raw = mapping.get("fps")
                try:
                    fps_val = int(fps_raw) if fps_raw is not None else None
                except (TypeError, ValueError):
                    fps_val = None
                mismatch = False
                if bitrate and preset.video_bitrate.lower() != bitrate:
                    mismatch = True
                if audio_bitrate and preset.audio_bitrate.lower() != audio_bitrate:
                    mismatch = True
                if fps_val is not None and preset.fps != fps_val:
                    mismatch = True
                if mismatch:
                    quality_name = ""
        if not quality_name:
            quality_name = _detect_quality_preset(mapping)
        if not quality_name:
            quality_name = str(data.get("quality_preset", "standard"))
        preset = resolve_quality_preset(quality_name)
        ffmpeg_raw = str(mapping.get("ffmpeg_path", data["ffmpeg_path"]) or "").strip()
        ffmpeg_path = Path(ffmpeg_raw).expanduser() if ffmpeg_raw else None
        audio_device = mapping.get("audio_device") or None
        video_source = str(mapping.get("video_source", data["video_source"]) or "desktop")
        settings = cls(
            save_directory=save_directory,
            quality_preset=preset.name,
            bitrate=preset.video_bitrate,
            audio_bitrate=preset.audio_bitrate,
            fps=preset.fps,
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
        quality = resolve_quality_preset(self.quality_preset)
        return {
            "save_directory": str(self.save_directory),
            "quality_preset": self.quality_preset,
            "quality_label": quality.label,
            "bitrate": self.bitrate,
            "audio_bitrate": self.audio_bitrate,
            "fps": self.fps,
            "profile": self.profile,
            "ffmpeg_path": str(self.ffmpeg_path) if self.ffmpeg_path else "",
            "auto_download_ffmpeg": self.auto_download_ffmpeg,
            "audio_device": self.audio_device or "",
            "video_source": self.video_source,
        }


def _detect_quality_preset(mapping: Mapping[str, Any]) -> str:
    """Infer the most suitable quality preset from legacy fields."""

    bitrate = str(mapping.get("bitrate", "")).strip().lower()
    audio_bitrate = str(mapping.get("audio_bitrate", "")).strip().lower()
    fps_raw = mapping.get("fps")
    try:
        fps = int(fps_raw) if fps_raw is not None else None
    except (TypeError, ValueError):
        fps = None

    for preset in QUALITY_PRESETS.values():
        if bitrate and preset.video_bitrate.lower() != bitrate:
            continue
        if audio_bitrate and preset.audio_bitrate.lower() != audio_bitrate:
            continue
        if fps is not None and preset.fps != fps:
            continue
        return preset.name
    return "standard"


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
