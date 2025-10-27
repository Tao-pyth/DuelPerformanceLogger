"""Build FFmpeg command sequences for recording and screenshots."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

__all__ = [
    "RecordingProfile",
    "PROFILE_PRESETS",
    "resolve_profile",
    "build_record_command",
    "build_screenshot_command",
]


@dataclass(frozen=True)
class RecordingProfile:
    """Definition of a capture profile consisting of width and height."""

    name: str
    width: int
    height: int

    @property
    def video_size(self) -> str:
        return f"{self.width}x{self.height}"


PROFILE_PRESETS: Mapping[str, RecordingProfile] = {
    "16:9": RecordingProfile("16:9", 1920, 1080),
    "21:9": RecordingProfile("21:9", 2560, 1080),
    "32:9": RecordingProfile("32:9", 3840, 1080),
}


def resolve_profile(name: str | None) -> RecordingProfile:
    key = (name or "16:9").strip()
    return PROFILE_PRESETS.get(key, PROFILE_PRESETS["16:9"])


def _base_command(executable: str | Path) -> list[str]:
    return [str(executable), "-y"]


def build_record_command(
    executable: str | Path,
    output_path: Path,
    *,
    fps: int,
    video_bitrate: str,
    audio_bitrate: str,
    profile: RecordingProfile,
    video_source: str = "desktop",
    audio_device: str | None = None,
    extra_args: Sequence[str] | None = None,
) -> list[str]:
    """Create an FFmpeg invocation for screen recording."""

    command = _base_command(executable)
    command.extend([
        "-f",
        "gdigrab",
        "-framerate",
        str(fps),
        "-video_size",
        profile.video_size,
        "-i",
        video_source,
    ])
    if audio_device:
        command.extend(["-f", "dshow", "-i", audio_device])
    command.extend([
        "-c:v",
        "libx264",
        "-b:v",
        video_bitrate,
        "-pix_fmt",
        "yuv420p",
    ])
    if audio_device:
        command.extend(["-c:a", "aac", "-b:a", audio_bitrate])
    command.append(str(output_path))
    if extra_args:
        command.extend(list(extra_args))
    return command


def build_screenshot_command(
    executable: str | Path,
    output_path: Path,
    *,
    profile: RecordingProfile,
    video_source: str = "desktop",
    extra_args: Iterable[str] | None = None,
) -> list[str]:
    """Create an FFmpeg invocation that captures a single frame."""

    command = _base_command(executable)
    command.extend([
        "-f",
        "gdigrab",
        "-video_size",
        profile.video_size,
        "-i",
        video_source,
        "-frames:v",
        "1",
        str(output_path),
    ])
    if extra_args:
        command.extend(list(extra_args))
    return command
