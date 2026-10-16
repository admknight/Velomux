"""Media conversion engine for Velomux v0.1.

No shell invocation. Originals are never modified. Completed outputs are staged
in the destination directory and atomically installed after validation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional
import json
import math
import os
import re
import shutil
from toolchain import find_tools
import subprocess
import tempfile
import threading
from collections import deque

from PIL import Image, ImageOps, ImageSequence, features

VIDEO_SUFFIXES = {'.mp4','.m4v','.mkv','.mov','.avi','.wmv','.webm','.flv','.mpg','.mpeg','.ts','.mts','.m2ts','.vob','.3gp','.ogv'}
AUDIO_SUFFIXES = {'.mp3','.m4a','.aac','.wav','.flac','.ogg','.oga','.opus','.wma','.aiff','.aif','.aifc','.ac3','.mka','.caf','.ape'}
IMAGE_SUFFIXES = {'.jpg','.jpeg','.png','.webp','.gif','.tif','.tiff','.bmp','.ico','.avif','.heic','.heif','.tga','.psd','.jfif'}
SUPPORTED_SUFFIXES = VIDEO_SUFFIXES | AUDIO_SUFFIXES | IMAGE_SUFFIXES

@dataclass(frozen=True)
class Preset:
    name: str
    group: str  # video, audio, image
    ext: str
    vcodec: str = ''
    acodec: str = ''
    bitrate: str = ''
    extra: tuple[str, ...] = ()

PRESETS: tuple[Preset, ...] = (
    Preset('MP4 - H.264 + AAC', 'video', '.mp4', 'libx264', 'aac', '192k'),
    Preset('MP4 - H.265 + AAC', 'video', '.mp4', 'libx265', 'aac', '192k'),
    Preset('MP4 - AV1 + AAC', 'video', '.mp4', 'libsvtav1', 'aac', '192k'),
    Preset('MKV - H.264 + AAC', 'video', '.mkv', 'libx264', 'aac', '192k'),
    Preset('MKV - H.265 + AAC', 'video', '.mkv', 'libx265', 'aac', '192k'),
    Preset('WebM - VP9 + Opus', 'video', '.webm', 'libvpx-vp9', 'libopus', '160k'),
    Preset('WebM - AV1 + Opus', 'video', '.webm', 'libsvtav1', 'libopus', '160k'),
    Preset('MOV - ProRes + PCM', 'video', '.mov', 'prores_ks', 'pcm_s16le'),
    Preset('MP4 - Remux / Stream copy', 'video', '.mp4', 'copy', 'copy'),
    Preset('MKV - Remux / Stream copy', 'video', '.mkv', 'copy', 'copy'),
    Preset('Animated GIF - Video to GIF', 'video', '.gif', 'gif', 'none'),
    Preset('M4A - AAC (smart copy)', 'audio', '.m4a', acodec='aac', bitrate='256k'),
    Preset('M4A - ALAC lossless', 'audio', '.m4a', acodec='alac'),
    Preset('MP3 - 320 kbps', 'audio', '.mp3', acodec='libmp3lame', bitrate='320k'),
    Preset('MP3 - 192 kbps', 'audio', '.mp3', acodec='libmp3lame', bitrate='192k'),
    Preset('FLAC - Lossless', 'audio', '.flac', acodec='flac'),
    Preset('WAV - PCM 16-bit', 'audio', '.wav', acodec='pcm_s16le'),
    Preset('Opus - 160 kbps', 'audio', '.opus', acodec='libopus', bitrate='160k'),
    Preset('OGG - Vorbis 192 kbps', 'audio', '.ogg', acodec='libvorbis', bitrate='192k'),
    Preset('JPEG - Quality controlled', 'image', '.jpg'),
    Preset('PNG - Lossless', 'image', '.png'),
    Preset('WebP - Quality controlled', 'image', '.webp'),
    Preset('TIFF - Lossless', 'image', '.tiff'),
    Preset('BMP - Uncompressed', 'image', '.bmp'),
    Preset('GIF - Image', 'image', '.gif'),
    Preset('AVIF - If supported', 'image', '.avif'),
)
PRESET_MAP = {p.name: p for p in PRESETS}

@dataclass
class Options:
    # collision: repair, overwrite, skip, rename
    collision: str = 'repair'
    quality: int = 23
    video_speed: str = 'medium'  # encoder preset
    video_width: int = 0
    video_height: int = 0
    fps: float = 0
    rotate_video: int = 0   # 0, 90, 180, 270 clockwise
    deinterlace: bool = False
    mute_video: bool = False
    trim_start: float = 0
    trim_end: float = 0  # zero means end of source
    audio_bitrate: int = 0  # zero -> preset bitrate
    audio_sample_rate: int = 0
    audio_channels: int = 0
    audio_normalize: bool = False
    audio_gain_db: float = 0
    media_speed: float = 1.0
    image_width: int = 0  # bounding box; preserve aspect ratio
    image_height: int = 0
    image_quality: int = 90
    rotate_image: int = 0
    flip_image: str = 'none'  # none, horizontal, vertical
    grayscale: bool = False
    keep_metadata: bool = True
    decode_check: bool = False  # full stream decode for validation (slow)

class ConversionError(Exception):
    pass

class CancelledError(ConversionError):
    pass

@dataclass
class Result:
    status: str  # done, skipped, failed, cancelled
    output: Optional[Path] = None
    detail: str = ''

# By using a unique prefix and same destination filesystem, os.replace is atomic.
WIN_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

def which_tools() -> tuple[Optional[str], Optional[str]]:
    return find_tools()

def classify(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in VIDEO_SUFFIXES: return 'video'
    if suffix in AUDIO_SUFFIXES: return 'audio'
    if suffix in IMAGE_SUFFIXES: return 'image'
    return 'unknown'

def compatibility(path: Path, preset: Preset) -> bool:
    kind = classify(path)
    return kind == 'image' if preset.group == 'image' else (kind in ('video','audio') if preset.group == 'audio' else kind == 'video')

def _run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=timeout, creationflags=WIN_NO_WINDOW)

def probe(path: Path, ffprobe: Optional[str] = None) -> dict:
    if classify(path) == 'image':
        with Image.open(path) as im:
            im.load()
            return {'category':'image', 'format': im.format, 'width': im.width,
                    'height': im.height, 'frames': getattr(im,'n_frames',1),
                    'mode': im.mode, 'bytes':path.stat().st_size}
    executable = ffprobe or which_tools()[1]
    if not executable:
        raise ConversionError('ffprobe not found. Install FFmpeg including ffprobe and add it to PATH.')
    cp = _run([executable, '-v','error','-show_format','-show_streams','-of','json', str(path)])
    if cp.returncode != 0:
        raise ConversionError(f'Cannot inspect {path.name}: {cp.stderr.strip()[:500]}')
    try:
        data = json.loads(cp.stdout)
    except ValueError as exc:
        raise ConversionError('Invalid ffprobe JSON.') from exc
    streams = data.get('streams') or []
    if not streams:
        raise ConversionError('No media streams detected.')
    data['category'] = classify(path)
    return data

def _duration(info: dict) -> float:
    # Prefer format duration (or the longest audio/video stream if unavailable).
    values = [info.get('format', {}).get('duration')]
    values.extend(x.get('duration') for x in info.get('streams',[]) if x.get('codec_type') in ('audio','video'))
    nums = []
    for value in values:
        try:
            number = float(value)
            if math.isfinite(number) and number > 0: nums.append(number)
        except (TypeError, ValueError): pass
    return nums[0] if nums else 0.0

def _stream(info: dict, stream_type: str) -> Optional[dict]:
    return next((s for s in info.get('streams',[]) if s.get('codec_type') == stream_type), None)

def _stream_duration(info: dict, stream_type: str) -> float:
    """Use the selected media stream's duration, not the container duration.

    Video often continues after its audio track ends. Comparing an extracted M4A
    with the longer video container incorrectly flags fully converted audio as bad.
    """
    stream = _stream(info, stream_type)
    if stream:
        try:
            seconds = float(stream.get('duration', ''))
            if math.isfinite(seconds) and seconds > 0:
                return seconds
        except (ValueError, TypeError):
            pass
        tags = stream.get('tags') or {}
        duration_tag = tags.get('DURATION') or tags.get('duration')
        if duration_tag:
            try:
                components = [float(part) for part in str(duration_tag).split(':')]
                if len(components) == 3:
                    seconds = components[0]*3600 + components[1]*60 + components[2]
                    if math.isfinite(seconds) and seconds > 0:
                        return seconds
            except (ValueError, TypeError):
                pass
        try:
            seconds = float(stream['duration_ts']) * float(stream['time_base'].split('/')[0]) / float(stream['time_base'].split('/')[1])
            if math.isfinite(seconds) and seconds > 0:
                return seconds
        except (KeyError, ValueError, TypeError, ZeroDivisionError):
            pass
    return _duration(info)


def _target_seconds(info: dict, options: Options, stream_type: str = 'video') -> float:
    total = _stream_duration(info, stream_type)
    if total <= 0: return 0
    start = options.trim_start
    end = min(total, options.trim_end) if options.trim_end else total
    return max(0.0, (end - start) / options.media_speed)

def describe(path: Path) -> str:
    info = probe(path)
    if info.get('category') == 'image':
        return (f"IMAGE  |  {info.get('format')}  |  {info['width']} x {info['height']}  |  "
                f"{info['frames']} frame(s)  |  {info['bytes']/1048576:.2f} MiB")
    lines = [f"FILE  |  {path.name}  |  {path.stat().st_size/1048576:.2f} MiB",
             f"Duration: {_duration(info):.2f} seconds"]
    for stream in info.get('streams', []):
        t = stream.get('codec_type','?')
        desc = f"{t.upper()}: {stream.get('codec_name','?')}"
        if t == 'video': desc += f" | {stream.get('width','?')}x{stream.get('height','?')} | {stream.get('r_frame_rate','?')} fps"
        if t == 'audio': desc += f" | {stream.get('sample_rate','?')} Hz | {stream.get('channels','?')} channels"
        if t == 'subtitle': desc += f" | {stream.get('tags',{}).get('language','unknown')}"
        lines.append(desc)
    return '\n'.join(lines)

def list_encoders() -> set[str]:
    exe = which_tools()[0]
    if not exe: return set()
    try:
        cp = _run([exe, '-hide_banner', '-encoders'], timeout=15)
        return set(re.findall(r'^\s*[VAS][A-Z.]{5}\s+([A-Za-z0-9][A-Za-z0-9_.+-]*)', cp.stdout, flags=re.M))
    except Exception: return set()

def resolve_output(source: Path, output_dir: Path, preset: Preset, collision: str,
                   output_stem: Optional[str] = None) -> Path:
    stem = source.stem if output_stem is None else output_stem
    if not stem or stem in ('.', '..') or any(c in stem for c in '/\\'):
        raise ConversionError('Invalid output name.')
    output = output_dir / (stem + preset.ext)
    # Never allow a conversion to replace its own source, even on overwrite.
    if os.path.normcase(os.path.abspath(str(output))) == os.path.normcase(os.path.abspath(str(source))):
        if collision != 'rename':
            raise ConversionError('Source and destination are the same file. Choose another output folder.')
    if collision == 'rename':
        number = 1
        while output.exists() or os.path.normcase(os.path.abspath(str(output))) == os.path.normcase(os.path.abspath(str(source))):
            output = output_dir / f'{stem} ({number}){preset.ext}'
            number += 1
    return output

def _codec_args(preset: Preset, source_info: dict, opt: Options) -> list[str]:
    cmd: list[str] = []
    audio = _stream(source_info, 'audio')
    if preset.group == 'audio':
        if audio is None: raise ConversionError('Input has no audio track.')
        cmd += ['-map','0:a:0','-vn','-sn','-dn']
        filter_list: list[str] = []
        if opt.audio_normalize: filter_list.append('loudnorm=I=-16:LRA=11:TP=-1.5')
        if abs(opt.audio_gain_db) > 0.001: filter_list.append(f'volume={opt.audio_gain_db:g}dB')
        if opt.media_speed != 1: filter_list.append(f'atempo={opt.media_speed:.6f}')
        if filter_list: cmd += ['-af', ','.join(filter_list)]
        # Smart copy means no generational loss if already AAC and no audio processing.
        can_copy = (preset.acodec == 'aac' and audio.get('codec_name') == 'aac'
                    and not filter_list and not opt.audio_sample_rate and not opt.audio_channels)
        if can_copy: cmd += ['-c:a','copy']
        else:
            cmd += ['-c:a', preset.acodec]
            kbps = opt.audio_bitrate if opt.audio_bitrate else int(preset.bitrate[:-1]) if preset.bitrate else 0
            if kbps and preset.acodec in ('aac','libmp3lame','libopus','libvorbis'):
                cmd += ['-b:a', f'{kbps}k']
            if opt.audio_sample_rate: cmd += ['-ar',str(opt.audio_sample_rate)]
            if opt.audio_channels: cmd += ['-ac',str(opt.audio_channels)]
        return cmd
    if preset.group != 'video':
        raise ConversionError('Not an FFmpeg preset.')
    if not _stream(source_info, 'video'):
        raise ConversionError('Input has no video track.')
    cmd += ['-map','0:v:0']
    if preset.vcodec == 'gif':
        filt = _video_filters(opt)
        filt.append('fps=12')
        # A direct GIF is supported; palette optimization can be added in a later version.
        cmd += ['-vf', ','.join(filt) if filt else 'fps=12', '-an','-sn','-dn']
        return cmd
    if not opt.mute_video and audio is not None: cmd += ['-map','0:a:0']
    if preset.vcodec == 'copy' and ( _video_filters(opt) or opt.fps or opt.media_speed != 1 or opt.audio_normalize
                                   or opt.audio_sample_rate or opt.audio_channels or opt.audio_gain_db):
        raise ConversionError('Remux/stream copy is incompatible with filters, speed or audio processing.')
    cmd += ['-c:v',preset.vcodec]
    if preset.vcodec != 'copy':
        vf = _video_filters(opt)
        if vf: cmd += ['-vf',','.join(vf)]
        if opt.fps: cmd += ['-r',str(opt.fps)]
        if preset.vcodec == 'prores_ks': cmd += ['-profile:v','3','-pix_fmt','yuv422p10le']
        elif preset.vcodec == 'libvpx-vp9':
            cmd += ['-crf',str(opt.quality),'-b:v','0','-deadline','good','-cpu-used','2', '-pix_fmt','yuv420p']
        elif preset.vcodec == 'libsvtav1':
            cmd += ['-crf',str(opt.quality), '-preset', '6', '-pix_fmt','yuv420p']
        else:
            cmd += ['-crf',str(opt.quality),'-preset',opt.video_speed,'-pix_fmt','yuv420p']
    if opt.mute_video or audio is None:
        cmd += ['-an']
    elif preset.acodec == 'copy':
        cmd += ['-c:a','copy']
    else:
        cmd += ['-c:a', preset.acodec]
        kbps = opt.audio_bitrate if opt.audio_bitrate else int(preset.bitrate[:-1]) if preset.bitrate else 0
        if kbps and preset.acodec in ('aac','libopus','libmp3lame','libvorbis'):
            cmd += ['-b:a',f'{kbps}k']
        af: list[str] = []
        if opt.audio_normalize: af.append('loudnorm=I=-16:LRA=11:TP=-1.5')
        if abs(opt.audio_gain_db) > 0.001: af.append(f'volume={opt.audio_gain_db:g}dB')
        if opt.media_speed != 1: af.append(f'atempo={opt.media_speed:.6f}')
        if af: cmd += ['-af',','.join(af)]
        if opt.audio_sample_rate: cmd += ['-ar',str(opt.audio_sample_rate)]
        if opt.audio_channels: cmd += ['-ac',str(opt.audio_channels)]
    if preset.ext == '.mp4' and preset.vcodec != 'copy': cmd += ['-movflags','+faststart']
    return cmd

def _video_filters(opt: Options) -> list[str]:
    vf=[]
    if opt.deinterlace: vf.append('yadif')
    if opt.video_width and opt.video_height:
        vf.append(f'scale={opt.video_width}:{opt.video_height}:force_original_aspect_ratio=decrease:force_divisible_by=2')
    elif opt.video_width: vf.append(f'scale={opt.video_width}:-2')
    elif opt.video_height: vf.append(f'scale=-2:{opt.video_height}')
    if opt.rotate_video == 90: vf.append('transpose=1')
    elif opt.rotate_video == 180: vf += ['hflip','vflip']
    elif opt.rotate_video == 270: vf.append('transpose=2')
    if opt.media_speed != 1: vf.append(f'setpts=PTS/{opt.media_speed:.6f}')
    return vf

def validate_options(opt: Options):
    if opt.collision not in {'repair','overwrite','skip','rename'}: raise ConversionError('Unknown collision mode.')
    if not (0 <= opt.quality <= 51): raise ConversionError('Video CRF must be between 0 and 51.')
    if opt.video_speed not in {'ultrafast','superfast','veryfast','faster','fast','medium','slow','slower','veryslow'}:
        raise ConversionError('Unknown video preset.')
    if not (1 <= opt.image_quality <= 100): raise ConversionError('Image quality must be 1 to 100.')
    if not (0.5 <= opt.media_speed <= 2.0): raise ConversionError('Playback speed must be between 0.5 and 2.0.')
    if opt.trim_start < 0 or opt.trim_end < 0: raise ConversionError('Trim timestamps cannot be negative.')
    if opt.trim_end and opt.trim_end <= opt.trim_start: raise ConversionError('Trim end must be after trim start.')
    if opt.video_width and (opt.video_width < 16 or opt.video_width%2): raise ConversionError('Video width must be even and at least 16.')
    if opt.video_height and (opt.video_height < 16 or opt.video_height%2): raise ConversionError('Video height must be even and at least 16.')
    if opt.fps and not (1 <= opt.fps <= 240): raise ConversionError('FPS must be 1 to 240.')
    if opt.rotate_video not in (0,90,180,270) or opt.rotate_image not in (0,90,180,270):
        raise ConversionError('Unsupported rotation.')
    if opt.audio_bitrate and not (32 <= opt.audio_bitrate <= 512):
        raise ConversionError('Audio bitrate must be between 32 and 512 kbps.')
    if opt.audio_sample_rate and not (8000 <= opt.audio_sample_rate <= 192000):
        raise ConversionError('Audio sample rate must be between 8000 and 192000 Hz.')
    if opt.audio_channels not in (0,1,2,6,8): raise ConversionError('Channels must be 0, 1, 2, 6 or 8.')
    if not (-40 <= opt.audio_gain_db <= 40): raise ConversionError('Audio gain must be -40 to +40 dB.')
    if opt.flip_image not in ('none','horizontal','vertical'): raise ConversionError('Invalid image flip setting.')
    for dimension in (opt.image_width,opt.image_height):
        if dimension and (dimension < 1 or dimension > 32768): raise ConversionError('Image dimensions must be 1 to 32768.')

def _image_transform(im: Image.Image, opt: Options) -> Image.Image:
    im = ImageOps.exif_transpose(im)
    if opt.image_width or opt.image_height:
        width = opt.image_width or im.width
        height = opt.image_height or im.height
        # Scale down/up only to fit within box, preserving aspect ratio.
        im = ImageOps.contain(im, (width,height), Image.Resampling.LANCZOS)
    if opt.rotate_image: im = im.rotate(-opt.rotate_image, expand=True)
    if opt.flip_image == 'horizontal': im = ImageOps.mirror(im)
    elif opt.flip_image == 'vertical': im = ImageOps.flip(im)
    if opt.grayscale: im = ImageOps.grayscale(im)
    return im

def _image_save(source: Path, temp: Path, preset: Preset, opt: Options,
                cb: Callable[[float,str],None], cancel: threading.Event) -> None:
    fmt={'.jpg':'JPEG','.png':'PNG','.webp':'WEBP','.tiff':'TIFF','.bmp':'BMP','.gif':'GIF','.avif':'AVIF'}[preset.ext]
    with Image.open(source) as source_im:
        frames = getattr(source_im, 'n_frames', 1)
        animated_output = frames > 1 and fmt in ('GIF','WEBP','TIFF')
        icc = source_im.info.get('icc_profile') if opt.keep_metadata else None
        # EXIF orientation must be reconciled with pixels; exif_transpose handles it.
        metadata = source_im.getexif() if opt.keep_metadata else None
        def normalize(im):
            if fmt in ('JPEG','BMP') and (im.mode not in ('RGB','L')):
                bg = Image.new('RGB', im.size, 'white')
                bg.paste(im.convert('RGBA'), mask=im.convert('RGBA').getchannel('A'))
                return bg
            if fmt == 'GIF' and im.mode not in ('RGB','RGBA','P','L'):
                return im.convert('RGBA')
            return im
        def ensure():
            if cancel.is_set(): raise CancelledError('Cancelled')
        kwargs = {}
        if fmt in ('JPEG','WEBP','AVIF'): kwargs['quality'] = opt.image_quality
        if fmt == 'JPEG': kwargs['optimize'] = True
        if fmt == 'PNG': kwargs['optimize'] = True
        if fmt == 'TIFF': kwargs['compression'] = 'tiff_deflate'
        if opt.keep_metadata and icc and fmt in ('JPEG','PNG','WEBP','TIFF'):
            kwargs['icc_profile'] = icc
        if opt.keep_metadata and metadata and fmt in ('JPEG','PNG','WEBP'):
            # EXIF has been rewritten by exif_transpose; use exif after transforming.
            kwargs['exif'] = ImageOps.exif_transpose(source_im).getexif().tobytes()
        if animated_output:
            processed=[]
            durations=[]
            for i, frame in enumerate(ImageSequence.Iterator(source_im)):
                ensure()
                processed.append(normalize(_image_transform(frame.copy(), opt)))
                durations.append(frame.info.get('duration',source_im.info.get('duration',100)))
                cb((i+1)*90/frames,f'Frame {i+1}/{frames}')
            kwargs['save_all']=True
            kwargs['append_images']=processed[1:]
            if fmt in ('GIF','WEBP'):
                kwargs['duration']=durations
                kwargs['loop']=source_im.info.get('loop',0)
            if fmt == 'GIF':
                kwargs.pop('exif', None)
                kwargs.pop('icc_profile', None)
            processed[0].save(temp, format=fmt, **kwargs)
        else:
            ensure()
            im = normalize(_image_transform(source_im.copy(),opt))
            im.save(temp, format=fmt, **kwargs)
        cb(95,'Validating image')

def validate_output(output: Path, preset: Preset, expected: float,
                    full_decode: bool = False, ffprobe: Optional[str] = None,
                    ffmpeg: Optional[str] = None) -> bool:
    """Verify readable output, matching media type/duration; full_decode optionally exhaustive.

    For stream-copy remux, duration can vary modestly due to packet timestamps.
    Validation is deliberately conservative about declaring *complete*.
    """
    try:
        if not output.is_file() or output.stat().st_size <= 0: return False
        if preset.group == 'image' or preset.vcodec == 'gif':
            with Image.open(output) as im:
                total_ms = 0
                for index in range(getattr(im,'n_frames',1)):
                    im.seek(index)
                    im.load()
                    total_ms += im.info.get('duration',0)
                if preset.vcodec == 'gif' and expected > 0 and total_ms:
                    if abs(total_ms/1000-expected) > max(1.0,expected*0.05):
                        return False
            return True
        info = probe(output, ffprobe=ffprobe)
        required = 'audio' if preset.group == 'audio' else 'video'
        if not _stream(info, required): return False
        duration = _duration(info)
        if expected > 0:
            # -r and stream-copy cuts may differ by a frame or audio packet.
            tolerance = max(2.0, expected * 0.02)
            if not (duration > 0 and abs(duration - expected) <= tolerance): return False
        if full_decode:
            exe = ffmpeg or which_tools()[0]
            if not exe: return False
            stream = '0:a:0' if required == 'audio' else '0:v:0'
            cp = _run([exe,'-hide_banner','-v','error','-xerror','-i',str(output),'-map',stream,
                       '-f','null','-'],timeout=3600)
            if cp.returncode != 0: return False
        return True
    except Exception:
        return False

def _hhmmss_to_seconds(time_str: str) -> float:
    try:
        a,b,c=time_str.split(':')
        return float(a)*3600+float(b)*60+float(c)
    except Exception: return 0.0

def _ffmpeg_convert(source: Path, temp: Path, preset: Preset, opt: Options, info: dict,
                    expected: float, cb: Callable[[float,str],None], cancel: threading.Event):
    ffmpeg, _ = which_tools()
    if not ffmpeg: raise ConversionError('ffmpeg not found in PATH.')
    if opt.trim_start and _duration(info) and opt.trim_start >= _duration(info):
        raise ConversionError('Trim start is beyond source duration.')
    args=[ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-y','-stats_period','0.5',
          '-progress','pipe:1']
    if opt.trim_start: args += ['-ss',str(opt.trim_start)]
    args += ['-i',str(source)]
    if opt.trim_end: args += ['-t',str(opt.trim_end - opt.trim_start)]
    args += _codec_args(preset, info, opt)
    if opt.keep_metadata: args += ['-map_metadata','0']
    else: args += ['-map_metadata','-1']
    args += [str(temp)]
    tail=deque(maxlen=25)
    process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                             stdin=subprocess.DEVNULL,universal_newlines=True,
                             bufsize=1,creationflags=WIN_NO_WINDOW)
    def drain_errors():
        for ln in iter(process.stderr.readline,''):
            tail.append(ln.strip())
    error_thread=threading.Thread(target=drain_errors, daemon=True)
    error_thread.start()
    try:
        for line in iter(process.stdout.readline,''):
            if cancel.is_set():
                process.terminate()
                break
            line = line.strip()
            if line.startswith('out_time='):
                secs = _hhmmss_to_seconds(line.split('=',1)[1])
                if expected: cb(min(98.0,secs*100/expected), f'{secs:.1f}s / {expected:.1f}s')
            elif line == 'progress=end': cb(99.0, 'Checking output')
        try:
            exitcode = process.wait(timeout=8 if cancel.is_set() else None)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            exitcode = -1
        error_thread.join(timeout=2)
        if cancel.is_set(): raise CancelledError('Conversion cancelled.')
        if exitcode != 0:
            raise ConversionError('FFmpeg error: ' + (' | '.join(tail)[-1400:] or f'exit code {exitcode}'))
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
        if process.stdout: process.stdout.close()
        if process.stderr: process.stderr.close()

def convert(source: Path | str, target_dir: Path | str, preset: Preset | str,
            opt: Optional[Options] = None,
            callback: Optional[Callable[[float,str],None]] = None,
            cancel: Optional[threading.Event] = None,
            output_stem: Optional[str] = None) -> Result:
    opt = opt or Options()
    callback = callback or (lambda progress, detail: None)
    cancel = cancel or threading.Event()
    if isinstance(preset,str):
        if preset not in PRESET_MAP: return Result('failed',detail='Unknown preset.')
        preset = PRESET_MAP[preset]
    try:
        validate_options(opt)
        source = Path(source).expanduser().resolve()
        target_dir = Path(target_dir).expanduser().resolve()
        if not source.is_file(): raise ConversionError(f'File does not exist: {source}')
        if not compatibility(source,preset):
            raise ConversionError(f'{source.suffix} input cannot use {preset.group} preset.')
        if cancel.is_set(): raise CancelledError('Cancelled.')
        target_dir.mkdir(parents=True,exist_ok=True)
        destination = resolve_output(source,target_dir,preset,opt.collision,output_stem)
        # Probe once before checking validity, and account for trim and speed.
        info = probe(source)
        expected = _target_seconds(info,opt, 'audio' if preset.group == 'audio' else 'video') if preset.group != 'image' else 0.0
        if preset.group != 'image' and expected <= 0 and opt.trim_end:
            raise ConversionError('Invalid trim range for this source.')
        if destination.exists():
            if opt.collision == 'skip': return Result('skipped',destination,'File already exists.')
            if opt.collision == 'repair' and validate_output(destination,preset,expected,opt.decode_check):
                return Result('skipped',destination,'Already complete and valid.')
        if cancel.is_set(): raise CancelledError('Cancelled.')
        fd,tempname=tempfile.mkstemp(prefix=f'.{source.stem[:35]}-',suffix=preset.ext,dir=target_dir)
        os.close(fd)
        temp=Path(tempname)
        try:
            if preset.group == 'image':
                _image_save(source,temp,preset,opt,callback,cancel)
            else:
                _ffmpeg_convert(source,temp,preset,opt,info,expected,callback,cancel)
            if cancel.is_set(): raise CancelledError('Cancelled before output replacement.')
            if not validate_output(temp,preset,expected,opt.decode_check):
                raise ConversionError('Output failed validation (size, stream or duration). Existing file untouched.')
            # os.replace is atomic on same volume, including Windows when target can be replaced.
            if os.path.normcase(os.path.abspath(str(temp))) == os.path.normcase(os.path.abspath(str(source))):
                raise ConversionError('Refusing to replace source.')
            if opt.collision == 'skip' and destination.exists():
                return Result('skipped',destination,'Created by another process.')
            os.replace(temp,destination)
            callback(100,'Completed')
            return Result('done',destination, 'Verified output saved.')
        finally:
            try:
                if temp.exists(): temp.unlink()
            except OSError: pass
    except CancelledError as exc: return Result('cancelled',detail=str(exc))
    except Exception as exc: return Result('failed',detail=str(exc))

