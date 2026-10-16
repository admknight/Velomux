"""Regression: source container duration must not invalidate extracted audio."""
from pathlib import Path
import subprocess

import pytest
from engine import Options, convert, probe, _duration, _stream_duration


@pytest.fixture
def video_outlives_audio(tmp_path):
    source = tmp_path / "A long video - short sound.mp4"
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-t", "7", "-i", "color=c=blue:s=160x120:r=12",
        "-f", "lavfi", "-t", "2", "-i", "sine=frequency=660:sample_rate=44100",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k", str(source),
    ]
    subprocess.run(command, check=True, timeout=60)
    return source


def test_extract_complete_aac_with_shorter_audio(video_outlives_audio, tmp_path):
    source_info = probe(video_outlives_audio)
    assert _duration(source_info) > 6.0
    assert 1.9 <= _stream_duration(source_info, "audio") <= 2.1
    destination = tmp_path / "Converted"
    outcome = convert(video_outlives_audio, destination,
                      "M4A - AAC (smart copy)", Options(decode_check=True))
    assert outcome.status == "done", outcome.detail
    assert outcome.output.is_file()
    assert 1.9 <= _duration(probe(outcome.output)) <= 2.1
    again = convert(video_outlives_audio, destination,
                    "M4A - AAC (smart copy)", Options(decode_check=True))
    assert again.status == "skipped", again.detail


def test_repair_short_audio_without_changing_source(video_outlives_audio, tmp_path):
    source_bytes = video_outlives_audio.read_bytes()
    folder = tmp_path / "Converted"
    folder.mkdir()
    bad = folder / (video_outlives_audio.stem + ".m4a")
    bad.write_bytes(b"")
    result = convert(video_outlives_audio, folder, "M4A - AAC (smart copy)")
    assert result.status == "done", result.detail
    assert bad.stat().st_size > 0
    assert video_outlives_audio.read_bytes() == source_bytes
