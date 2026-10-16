"""VeloFlow: curated, task-first profiles exclusive to the Velomux UI.

The profile catalog maps to tested engine presets; it never substitutes a
codec or silently changes the operation selected by a user.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from engine import PRESET_MAP


@dataclass(frozen=True)
class FlowProfile:
    id: str
    label: str
    detail: str
    preset: str


@dataclass(frozen=True)
class FlowTask:
    id: str
    title: str
    tagline: str
    input_kinds: tuple[str, ...]
    profiles: tuple[FlowProfile, ...]
    warning: str = ""


def profile(id: str, label: str, detail: str, preset: str) -> FlowProfile:
    if preset not in PRESET_MAP:
        raise ValueError(f"VeloFlow profile {id!r} refers to missing engine preset {preset!r}")
    return FlowProfile(id, label, detail, preset)


FLOWS: tuple[FlowTask, ...] = (
    FlowTask("video", "Video", "Everyday playback and high-quality exports",
             ("video",), (
                 profile("video-everyday", "Everyday MP4", "H.264 + AAC · broadly compatible playback", "MP4 - H.264 + AAC"),
                 profile("video-quality", "High-quality MP4", "H.264 · higher-quality encode, larger output possible", "MP4 - H.264 high quality"),
                 profile("video-speed", "Fast MP4", "H.264 · faster encoding with speed tradeoffs", "MP4 - H.264 fast encoding"),
                 profile("video-hevc", "Modern H.265", "HEVC + AAC · check device compatibility", "MP4 - H.265 + AAC"),
                 profile("video-webm", "WebM VP9", "VP9 + Opus · for compatible players", "WebM - VP9 + Opus"),
             )),
    FlowTask("audio", "Audio", "Music, podcasts and lossless collections",
             ("audio",), (
                 profile("audio-mp3", "MP3 · Everyday", "192 kbps · compatible with most players", "MP3 - 192 kbps"),
                 profile("audio-mp3hi", "MP3 · High bitrate", "320 kbps · preserves more detail from suitable sources", "MP3 - 320 kbps"),
                 profile("audio-m4a", "M4A · AAC", "192 kbps · efficient audio encoding", "M4A - AAC 192 kbps"),
                 profile("audio-flac", "FLAC · Lossless", "Lossless output; cannot restore already lost source quality", "FLAC - Lossless"),
                 profile("audio-wav", "WAV · Uncompressed", "16-bit PCM · larger file size", "WAV - PCM 16-bit"),
                 profile("audio-opus", "Opus · Compact", "96 kbps · efficient for speech and portable listening", "Opus - 96 kbps"),
             )),
    FlowTask("images", "Images", "Photos, transparency and web-ready assets",
             ("image",), (
                 profile("image-jpg", "JPEG · High quality", "Quality 95 · suitable for photographs", "JPEG - High quality (95)"),
                 profile("image-jpgsmall", "JPEG · Compact", "Quality 70 · smaller output with more compression", "JPEG - Compact (70)"),
                 profile("image-png", "PNG · Lossless", "Preserves image fidelity and transparency", "PNG - Lossless"),
                 profile("image-webp", "WebP · Compact", "Quality 65 · efficient web images", "WebP - Compact (65)"),
                 profile("image-webploss", "WebP · Lossless", "Pixel-preserving WebP output where supported", "WebP - Lossless"),
                 profile("image-icon", "Windows icon", "ICO · for app icons and shortcuts", "ICO - Windows icon"),
             )),
    FlowTask("extract", "Extract audio", "Take the soundtrack out of a video",
             ("video",), (
                 profile("extract-m4a", "Original AAC → M4A", "Copies AAC without re-encoding where possible; otherwise AAC encoding", "M4A - AAC (smart copy)"),
                 profile("extract-mp3", "Extract to MP3", "192 kbps · universally playable audio", "MP3 - 192 kbps"),
                 profile("extract-flac", "Extract to FLAC", "Lossless output file; no recovery of source compression losses", "FLAC - Lossless"),
                 profile("extract-wav", "Extract to WAV", "16-bit uncompressed PCM", "WAV - PCM 16-bit"),
             )),
    FlowTask("compress", "Compress", "Smaller video with adjustable quality tradeoffs",
             ("video",), (
                 profile("compress-compact", "Compact MP4", "H.264 CRF 28 · result size depends on content", "MP4 - H.264 compact"),
                 profile("compress-hevc", "Efficient H.265", "HEVC + AAC · more demanding to decode", "MP4 - H.265 + AAC"),
                 profile("compress-fast", "Fast smaller MP4", "Faster H.264 encoding; not a guaranteed smaller file", "MP4 - H.264 fast encoding"),
             )),
    FlowTask("rewrap", "Rewrap", "Change container, keep compatible streams",
             ("video",), (
                 profile("rewrap-mkv", "Copy streams → MKV", "No re-encoding · streams must fit container", "MKV - Remux / Stream copy"),
                 profile("rewrap-mp4", "Copy streams → MP4", "No re-encoding · some tracks may be incompatible", "MP4 - Remux / Stream copy"),
                 profile("rewrap-mov", "Copy streams → MOV", "No re-encoding · streams must fit MOV", "MOV - Remux / Stream copy"),
             ), "Changing the container does not make an unsupported codec playable."),
    FlowTask("trim", "Trim", "Keep just the part of a video you need",
             ("video",), (
                 profile("trim-quick", "Fast trim · Keyframes", "No re-encoding via MKV stream copy · cut points may align to keyframes", "MKV - Remux / Stream copy"),
                 profile("trim-accurate", "Accurate trim · Re-encode", "H.264 + AAC · for precise cuts, with re-encoding", "MP4 - H.264 + AAC"),
             ), "Set a start and end time before converting. Fast copy cuts may not be frame-accurate."),
)

FLOWS_BY_ID = {flow.id: flow for flow in FLOWS}
PROFILE_BY_ID = {p.id: p for flow in FLOWS for p in flow.profiles}

# Only an initial proposal. Users must explicitly click Convert to act on it.
AUTOMATIC_BY_KIND = {
    "video": "MP4 - H.264 + AAC",
    "audio": "MP3 - 192 kbps",
    "image": "PNG - Lossless",
}


def recommended_preset(kind: str, task_id: Optional[str] = None,
                       profile_id: Optional[str] = None) -> Optional[str]:
    """Return an explicitly selected task's profile or a compatible default.

    Never silently turn a video import into audio extraction just because the
    engine accepts video sources for audio output.
    """
    if not task_id:
        return AUTOMATIC_BY_KIND.get(kind)
    task = FLOWS_BY_ID.get(task_id)
    if task is None or kind not in task.input_kinds:
        return None
    if profile_id:
        chosen = PROFILE_BY_ID.get(profile_id)
        if chosen not in task.profiles:
            return None
        return chosen.preset
    return task.profiles[0].preset


def destination_for(source: Path, custom_base: Path,
                    import_root: Optional[Path], preserve_tree: bool) -> Path:
    """Preserve imported relative folder hierarchy, never allow path traversal."""
    if not preserve_tree or import_root is None:
        return custom_base
    try:
        relative = source.resolve().relative_to(import_root.resolve())
    except ValueError:
        return custom_base
    safe_parts = relative.parts[:-1]
    if not safe_parts or any(part in ('..', '') for part in safe_parts):
        return custom_base
    return custom_base.joinpath(*safe_parts)


def media_paths_from_arguments(arguments: list[str]) -> list[Path]:
    """Safe Explorer entry point: accept actual local media files, no shell calls.

    Unsupported or nonexistent paths are ignored; a GUI launch never converts
    automatically. One Explorer selection may launch one application instance.
    """
    from engine import SUPPORTED_SUFFIXES
    found: list[Path] = []
    seen: set[str] = set()
    for item in arguments:
        path = Path(item).expanduser()
        if (not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES):
            continue
        canonical = path.resolve()
        key = str(canonical).casefold()
        if key not in seen:
            seen.add(key)
            found.append(canonical)
    return found
