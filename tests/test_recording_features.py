from __future__ import annotations

from pathlib import Path
from typing import Any

from app.function.core import (
    config_handler,
    ffmpeg_command_builder,
    file_sanitizer,
    record_integrity,
    recorder,
    session_logging,
)


def test_recording_settings_round_trip(tmp_path: Path) -> None:
    settings_path = tmp_path / "app_settings.json"
    initial = {
        "recording": {
            "save_directory": str(tmp_path / "captures"),
            "bitrate": "4000k",
            "audio_bitrate": "128k",
            "fps": 30,
            "profile": "21:9",
            "ffmpeg_path": str(tmp_path / "ffmpeg.exe"),
            "auto_download_ffmpeg": True,
            "audio_device": "microphone",
            "video_source": "desktop",
        }
    }
    config_handler.save_app_settings(initial, settings_path)

    loaded = config_handler.load_recording_settings(settings_path)
    assert loaded.quality_preset == "light"
    assert loaded.bitrate == "4000k"
    assert loaded.profile == "21:9"
    assert loaded.save_directory.exists()

    updated = config_handler.RecordingSettings.from_mapping(
        {**loaded.to_dict(), "quality_preset": "high"},
        prefer_explicit=True,
    )
    payload = config_handler.update_recording_settings(updated)
    assert payload["recording"]["quality_preset"] == "high"
    assert payload["recording"]["bitrate"] == "12000k"


def test_command_builder_profiles() -> None:
    profile = ffmpeg_command_builder.resolve_profile("21:9")
    quality = ffmpeg_command_builder.resolve_quality_preset("standard")
    command = ffmpeg_command_builder.build_record_command(
        "ffmpeg",
        Path("output.mp4"),
        quality=quality,
        profile=profile,
    )
    assert "-video_size" in command
    size_index = command.index("-video_size")
    assert command[size_index + 1] == "2560x1080"


def test_file_sanitizer_removes_invalid_characters() -> None:
    sanitized = file_sanitizer.sanitize_filename(" :/試合#1 ")
    assert sanitized.startswith("_") is False
    assert all(ch not in sanitized for ch in " :/#")


def test_integrity_retry(tmp_path: Path) -> None:
    target = tmp_path / "recording.mp4"
    target.write_bytes(b"")

    def retry() -> Path:
        target.write_bytes(b"x" * 4096)
        return target

    assert record_integrity.ensure_integrity(target, retries=1, retry_action=retry)


def test_session_logger_creates_structure(tmp_path: Path) -> None:
    logger = session_logging.RecordingSessionLogger(root=tmp_path)
    log_file = logger.log_path()
    assert log_file.parent.is_dir()
    assert logger.session_dir is not None


class DummyProcess:
    def __init__(self, command: list[str], **kwargs: Any) -> None:
        self.command = command
        self.kwargs = kwargs
        self.terminated = False
        self.killed = False

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: float | None = None) -> int:  # noqa: ARG002
        return 0

    def kill(self) -> None:
        self.killed = True


class FakeDatabase:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def record_recording(self, match_id: int, file_path: Path, **kwargs: Any) -> None:
        payload = {"match_id": match_id, "file_path": Path(file_path)}
        payload.update(kwargs)
        self.calls.append(payload)


def test_ffmpeg_recorder_start_stop_registers(tmp_path: Path) -> None:
    capture_dir = tmp_path / "captures"
    capture_dir.mkdir()
    ffmpeg_path = tmp_path / "ffmpeg"
    ffmpeg_path.write_text("#!/bin/sh\n", encoding="utf-8")

    quality = ffmpeg_command_builder.resolve_quality_preset("light")
    settings = config_handler.RecordingSettings(
        save_directory=capture_dir,
        quality_preset=quality.name,
        bitrate=quality.video_bitrate,
        audio_bitrate=quality.audio_bitrate,
        fps=quality.fps,
        profile="16:9",
        ffmpeg_path=ffmpeg_path,
        auto_download_ffmpeg=False,
        audio_device=None,
        video_source="desktop",
    )
    settings.ensure_directories()

    processes: list[DummyProcess] = []

    def factory(command: list[str], **kwargs: Any) -> DummyProcess:
        proc = DummyProcess(command, **kwargs)
        processes.append(proc)
        return proc

    logger = session_logging.RecordingSessionLogger(root=tmp_path / "logs")
    fake_db = FakeDatabase()

    rec = recorder.FFmpegRecorder(
        settings,
        process_factory=factory,
        integrity_checker=lambda path: True,
        session_logger=logger,
        database=fake_db,
    )

    for index in range(5):
        match_id = 42 + index
        output_path = rec.start(match_id=match_id)
        assert output_path.parent == capture_dir
        assert output_path.suffix == ".mp4"
        assert processes and processes[-1].command[0] == str(ffmpeg_path)

        result = rec.stop(match_id=match_id)
        assert result.status == "completed"
        assert processes[-1].terminated is True

    assert len(fake_db.calls) == 5
    assert fake_db.calls[0]["match_id"] == 42
    assert logger.session_dir is not None and logger.log_path().parent.exists()
