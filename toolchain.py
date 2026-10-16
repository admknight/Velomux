"""Find FFmpeg tools: explicit vetted bundle first, then development PATH.

Bundled folders are searched without shell execution and without downloading anything.
The FFmpeg executable and ffprobe executable must come from the same directory.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Optional


def candidate_directories() -> list[Path]:
    project = Path(__file__).resolve().parent
    dirs: list[Path] = []
    # PyInstaller stores --add-binary/--add-data in its internal resource folder.
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        dirs.extend([Path(meipass) / 'vendor' / 'ffmpeg' / 'bin', Path(meipass) / 'bin'])
    # Portable distribution and source tree, respectively.
    dirs.extend([
        Path(sys.executable).resolve().parent / 'vendor' / 'ffmpeg' / 'bin',
        project / 'vendor' / 'ffmpeg' / 'bin',
    ])
    seen: set[str] = set()
    unique = []
    for path in dirs:
        p = str(path)
        if p not in seen:
            unique.append(path)
            seen.add(p)
    return unique


def find_tools() -> tuple[Optional[str], Optional[str]]:
    names = ('ffmpeg.exe', 'ffprobe.exe') if os.name == 'nt' else ('ffmpeg', 'ffprobe')
    for folder in candidate_directories():
        a, b = (folder / names[0], folder / names[1])
        if a.is_file() and b.is_file():
            return str(a), str(b)
    a, b = shutil.which('ffmpeg'), shutil.which('ffprobe')
    # Never pair tools from unrelated PATH installations: capabilities, versions
    # and diagnostics could disagree in source-development fallback mode.
    if a and b and Path(a).parent.resolve() == Path(b).parent.resolve():
        return a, b
    return None, None


def tools_origin() -> str:
    a, b = find_tools()
    if not a or not b:
        return 'Missing (FFmpeg and ffprobe are required for video/audio)'
    if Path(a).parent == Path(b).parent and any(Path(a).parent == p for p in candidate_directories()):
        return 'Bundled FFmpeg'
    return 'System FFmpeg (development fallback)'
