"""Stream-copy must preserve all compatible tracks, never silently drop them."""
import subprocess

from engine import PRESET_MAP, Options, _codec_args, convert, probe


def test_remux_ffmpeg_arguments_map_multiple_audio_and_subtitle_tracks():
    info = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264"},
            {"codec_type": "audio", "codec_name": "aac"},
            {"codec_type": "audio", "codec_name": "aac"},
            {"codec_type": "subtitle", "codec_name": "subrip"},
        ]
    }
    preset = PRESET_MAP["MKV - Remux / Stream copy"]
    args = _codec_args(preset, info, Options())
    assert args.count("-map") == 3
    assert "0:v?" in args and "0:a?" in args and "0:s?" in args
    assert args[-2:] == ["-c", "copy"]
    mute = _codec_args(preset, info, Options(mute_video=True))
    assert "0:a?" not in mute
    assert "0:s?" in mute


def test_remux_keeps_two_audio_tracks(tmp_path):
    source = tmp_path / "Bilingual training video.mp4"
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi", "-t", "3", "-i", "color=c=blue:s=160x120:r=12",
        "-f", "lavfi", "-t", "3", "-i", "sine=frequency=300:sample_rate=44100",
        "-f", "lavfi", "-t", "3", "-i", "sine=frequency=660:sample_rate=44100",
        "-map", "0:v:0", "-map", "1:a:0", "-map", "2:a:0",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "96k",
        str(source),
    ]
    subprocess.run(command, check=True, capture_output=True, timeout=90)
    before = probe(source)
    result = convert(source, tmp_path / "Converted", "MKV - Remux / Stream copy")
    assert result.status == "done", result.detail
    after = probe(result.output)
    for kind, count in (("video", 1), ("audio", 2)):
        assert sum(x.get("codec_type") == kind for x in before["streams"]) == count
        assert sum(x.get("codec_type") == kind for x in after["streams"]) == count
    assert source.exists(), "Remux must preserve input source"
