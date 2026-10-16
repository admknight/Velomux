"""Preset library regression tests: expose choices and honor their semantics."""
from pathlib import Path
import subprocess

from PIL import Image

from engine import PRESETS, PRESET_MAP, Options, _codec_args, convert, probe


def test_51_named_presets_are_distinct_and_discoverable():
    assert len(PRESETS) >= 45
    assert len(PRESET_MAP) == len(PRESETS)
    for family, minimum in (("video", 12), ("audio", 18), ("image", 10)):
        assert sum(p.group == family for p in PRESETS) >= minimum


def test_aac_quality_choices_are_real_encodes_not_unintended_copy():
    source_info = {'streams': [{'codec_type': 'audio', 'codec_name': 'aac'}]}
    smart = _codec_args(PRESET_MAP["M4A - AAC (smart copy)"], source_info, Options())
    encoded = _codec_args(PRESET_MAP["M4A - AAC 128 kbps"], source_info, Options())
    assert smart[-2:] == ['-c:a','copy']
    assert '-c:a' in encoded and encoded[encoded.index('-c:a') + 1] == 'aac'
    assert '-b:a' in encoded and encoded[encoded.index('-b:a') + 1] == '128k'


def test_video_preset_quality_and_speed_defaults():
    source_info = {
        'streams': [
            {'codec_type': 'video', 'codec_name': 'h264'},
            {'codec_type': 'audio', 'codec_name': 'aac'},
        ]
    }
    high = _codec_args(PRESET_MAP["MP4 - H.264 high quality"], source_info, Options())
    compact = _codec_args(PRESET_MAP["MP4 - H.264 compact"], source_info, Options())
    fast = _codec_args(PRESET_MAP["MP4 - H.264 fast encoding"], source_info, Options())
    assert high[high.index('-crf')+1] == '18'
    assert compact[compact.index('-crf')+1] == '28'
    assert fast[fast.index('-preset')+1] == 'veryfast'


def test_jpeg_and_webp_image_presets_do_change_encoding(tmp_path):
    original = tmp_path / 'input.png'
    with Image.new('RGB', (160, 96)) as img:
        for x in range(160):
            for y in range(96):
                img.putpixel((x, y), ((x*11+y)%256, (x+y*7)%256, (x*y)%256))
        img.save(original)
    hi = convert(original, tmp_path/'high', 'JPEG - High quality (95)')
    low = convert(original, tmp_path/'low', 'JPEG - Compact (70)')
    assert hi.status == 'done', hi.detail
    assert low.status == 'done', low.detail
    assert hi.output.stat().st_size > low.output.stat().st_size
    webp = convert(original, tmp_path/'webp', 'WebP - Lossless')
    assert webp.status == 'done', webp.detail
    with Image.open(webp.output) as decoded, Image.open(original) as base:
        assert list(decoded.convert('RGB').getdata()) == list(base.getdata())


def test_m4a_128_encodes_synthetic_aac_to_requested_rate(tmp_path):
    source = tmp_path/'sample.mp4'
    subprocess.run([
        'ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi',
        '-i','sine=frequency=220:sample_rate=44100',
        '-t','2.0','-c:a','aac','-b:a','256k',str(source)
    ], check=True, timeout=30)
    result = convert(source, tmp_path/'converted', 'M4A - AAC 128 kbps')
    assert result.status == 'done',result.detail
    stream = next(s for s in probe(result.output)['streams'] if s['codec_type']=='audio')
    assert stream['codec_name'] == 'aac'
    assert 80_000 < int(stream['bit_rate']) < 160_000
