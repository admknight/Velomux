from pathlib import Path
import os

import toolchain


def test_bundled_pair_prioritized(tmp_path, monkeypatch):
    folder = tmp_path / 'vendor' / 'ffmpeg' / 'bin'
    folder.mkdir(parents=True)
    names = ('ffmpeg.exe', 'ffprobe.exe') if os.name == 'nt' else ('ffmpeg', 'ffprobe')
    ffmpeg, ffprobe = (folder / name for name in names)
    ffmpeg.write_bytes(b'placeholder')
    ffprobe.write_bytes(b'placeholder')
    monkeypatch.setattr(toolchain, 'candidate_directories', lambda: [folder])
    monkeypatch.setattr(toolchain.shutil, 'which', lambda _: '/wrong/ffmpeg')
    assert toolchain.find_tools() == (str(ffmpeg), str(ffprobe))
    assert toolchain.tools_origin() == 'Bundled FFmpeg'


def test_no_mixed_tool_versions(tmp_path, monkeypatch):
    folder = tmp_path / 'broken-bundle'
    folder.mkdir()
    name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
    (folder / name).write_bytes(b'placeholder')
    monkeypatch.setattr(toolchain, 'candidate_directories', lambda: [folder])
    monkeypatch.setattr(toolchain.shutil, 'which', lambda _: None)
    assert toolchain.find_tools() == (None, None)


def test_encoder_parser_identifies_flagged_encoders(monkeypatch):
    import subprocess
    import engine
    sample = '''Encoders:
 V..... = Video
 V....D libx264            H.264
 VFS..D libx265            HEVC
 A..... aac                AAC
 A..X.. libopus            Opus
'''
    monkeypatch.setattr(engine, 'which_tools', lambda: ('ffmpeg', 'ffprobe'))
    monkeypatch.setattr(engine, '_run',lambda *a,**k: subprocess.CompletedProcess([],0,sample,''))
    assert engine.list_encoders() == {'libx264','libx265','aac','libopus'}


def test_system_fallback_rejects_mismatched_ffmpeg_and_ffprobe(tmp_path, monkeypatch):
    monkeypatch.setattr(toolchain, 'candidate_directories', lambda: [])
    ffmpeg = str(tmp_path / 'engineA' / 'ffmpeg')
    ffprobe = str(tmp_path / 'engineB' / 'ffprobe')
    monkeypatch.setattr(toolchain.shutil, 'which',
                        lambda tool: ffmpeg if tool == 'ffmpeg' else ffprobe)
    assert toolchain.find_tools() == (None, None)
