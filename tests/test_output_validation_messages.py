"""Diagnostics must tell the user WHY an otherwise generated file was rejected."""
from pathlib import Path
import subprocess

from engine import PRESET_MAP, validate_output, validation_detail


def test_zero_byte_output_has_specific_reason(tmp_path):
    source = tmp_path/'empty.m4a'
    source.write_bytes(b'')
    preset = PRESET_MAP['M4A - AAC (smart copy)']
    valid, reason = validation_detail(source, preset, expected=2.0)
    assert not valid
    assert '0 bytes' in reason
    assert not validate_output(source, preset, expected=2.0)


def test_audio_duration_mismatch_has_numbers_and_remains_rejected(tmp_path):
    output = tmp_path/'audio.m4a'
    subprocess.run([
        'ffmpeg','-hide_banner','-loglevel','error','-y',
        '-f','lavfi','-t','2','-i','sine=frequency=440:sample_rate=44100',
        '-c:a','aac','-b:a','128k',str(output)
    ],check=True,capture_output=True,timeout=60)
    preset = PRESET_MAP['M4A - AAC 192 kbps']
    accepted, reason = validation_detail(output, preset, expected=30.0)
    assert not accepted
    assert 'duration mismatch' in reason
    assert '30.00s' in reason
    assert '2.00s' in reason or '2.02s' in reason
    assert not validate_output(output, preset, expected=30.0)
    valid, _ = validation_detail(output, preset, expected=2.0)
    assert valid
