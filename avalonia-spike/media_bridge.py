"""Velomux native Avalonia UI bridge to the preserved Python conversion engine.

Protocol: one JSON request per process on stdin, newline-delimited JSON events
on stdout. No shells, no Python installation on the end-user machine.
"""
from __future__ import annotations

import dataclasses
import json
import math
import sys
import tempfile
import threading
from pathlib import Path

# Running this file directly from its subdirectory must locate the repository
# engine module; PyInstaller also receives the repository root via --paths.
root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from engine import (
    PRESETS, PRESET_MAP, Options, SUPPORTED_SUFFIXES, VIDEO_SUFFIXES,
    AUDIO_SUFFIXES, IMAGE_SUFFIXES, convert, describe, which_tools,
)
from velomux_flows import FLOWS


def emit(**fields):
    sys.stdout.write(json.dumps(fields, ensure_ascii=False, allow_nan=False) + "\n")
    sys.stdout.flush()


def catalog():
    return {
        "version": "0.4.0",
        "presets": [
            {"name": p.name, "group": p.group, "ext": p.ext}
            for p in PRESETS
        ],
        "tasks": [
            {
                "id": task.id, "title": task.title,
                "tagline": task.tagline,
                "inputKinds": list(task.input_kinds),
                "warning": task.warning,
                "profiles": [
                    {"id": p.id, "label": p.label,
                     "detail": p.detail, "preset": p.preset}
                    for p in task.profiles
                ],
            }
            for task in FLOWS
        ],
        "suffixes": {
            "video": sorted(VIDEO_SUFFIXES),
            "audio": sorted(AUDIO_SUFFIXES),
            "image": sorted(IMAGE_SUFFIXES),
        },
    }


def read_request():
    text = sys.stdin.readline(524288)
    if not text:
        raise ValueError("Empty conversion request.")
    request = json.loads(text)
    if not isinstance(request, dict):
        raise ValueError("Conversion request must be a JSON object.")
    return request


def convert_request(request):
    source = request.get("source")
    directory = request.get("destination")
    preset = request.get("preset")
    if not all(isinstance(item, str) and item.strip()
               for item in (source, directory, preset)):
        raise ValueError("Source, destination and preset are required.")
    if preset not in PRESET_MAP:
        raise ValueError("Unknown engine preset: " + str(preset))
    provided = request.get("options") or {}
    if not isinstance(provided, dict):
        raise ValueError("Options must be a JSON object.")
    fields = {f.name for f in dataclasses.fields(Options)}
    unknown = set(provided) - fields
    if unknown:
        raise ValueError("Unsupported conversion option: " + ", ".join(sorted(unknown)))
    opts = Options(**provided)
    cancel = threading.Event()

    # Windows stdout/stderr pipes are redirected. Receive CANCEL without
    # requiring forced termination during a long-running FFmpeg operation.
    def cancellation_reader():
        try:
            for line in sys.stdin:
                if line.strip() == "CANCEL":
                    cancel.set()
                    break
        except (OSError, UnicodeError):
            pass

    threading.Thread(target=cancellation_reader, daemon=True).start()

    def on_progress(percent, detail):
        try:
            num = float(percent)
            num = min(100, max(0, num)) if math.isfinite(num) else 0
        except (ValueError, TypeError):
            num = 0
        emit(event="progress", percent=num, detail=str(detail)[:400])

    result = convert(
        Path(source), Path(directory), preset, opts,
        callback=on_progress, cancel=cancel,
    )
    emit(event="result", status=result.status,
         output=str(result.output) if result.output else "",
         detail=result.detail)
    return 0 if result.status in ("done", "skipped") else (
        3 if result.status == "cancelled" else 2
    )


def integration_test():
    """End-to-end checks of each existing task family against the real engine."""
    import subprocess
    from PIL import Image

    assert len(PRESETS) == 51, "Preset catalog changed unexpectedly"
    assert len(FLOWS) == 7, "Task catalog changed unexpectedly"
    assert sum(len(x.profiles) for x in FLOWS) == 29, "Purpose-profile catalog changed"
    ffmpeg, ffprobe = which_tools()
    assert ffmpeg and ffprobe, "Bundled matched FFmpeg/ffprobe are missing"
    with tempfile.TemporaryDirectory(prefix="Velomux-Avalonia-QA-") as root:
        root = Path(root)
        source = root / "Video - Unicode - \u0394 \u6d4b\u8bd5.mp4"
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-t", "7", "-i", "color=c=blue:s=160x120:r=12",
            "-f", "lavfi", "-t", "2", "-i", "sine=frequency=660:sample_rate=44100",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", str(source),
        ]
        completed = subprocess.run(command, capture_output=True, timeout=90)
        assert completed.returncode == 0, completed.stderr.decode(errors="replace")[-1200:]
        photo = root / "Photo - \u6d4b\u8bd5.png"
        Image.new("RGB", (160, 120), (35, 125, 220)).save(photo)
        outputs = root / "Outputs"
        cases = [
            (source, "MP4 - H.264 + AAC", Options(collision="rename")),
            (source, "MP3 - 192 kbps", Options(collision="rename")),
            (photo, "WebP - Lossless", Options(collision="rename")),
            (source, "M4A - AAC (smart copy)", Options(collision="rename", decode_check=True)),
            (source, "MP4 - H.264 compact", Options(collision="rename")),
            (source, "MKV - Remux / Stream copy", Options(collision="rename")),
            (source, "MKV - Remux / Stream copy", Options(
                collision="rename", trim_start=1, trim_end=3)),
        ]
        for source_file, preset, options in cases:
            outcome = convert(source_file, outputs, preset, options)
            if outcome.status != "done" or not outcome.output or not outcome.output.is_file():
                raise RuntimeError(f"{preset}: {outcome.status}: {outcome.detail}")
            if outcome.output.stat().st_size < 1:
                raise RuntimeError(f"{preset} generated empty output")
        assert source.is_file() and photo.is_file()
    emit(event="selftest", status="passed", cases=len(cases))
    return 0


def main():
    command = sys.argv[1] if len(sys.argv) > 1 else ""
    try:
        if command == "--catalog":
            emit(event="catalog", **catalog())
            return 0
        if command == "--describe":
            request = read_request()
            emit(event="description", detail=describe(Path(request["source"])))
            return 0
        if command == "--convert":
            return convert_request(read_request())
        if command == "--integration-test":
            return integration_test()
        emit(event="error", detail="Unknown bridge command.")
        return 5
    except Exception as exc:
        emit(event="error", detail=str(exc))
        return 2


if __name__ == "__main__":
    sys.exit(main())
