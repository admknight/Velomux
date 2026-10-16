# Velomux

**Convert your media, your way.**

Velomux is a standalone, offline-first Windows media converter under active development. It processes video, audio and images through FFmpeg/ffprobe and Pillow, with a modern Qt 6 interface, drag-and-drop batch queue, presets, advanced controls and safe output replacement.

**Status:** `0.2.1-preview`, a private test/build candidate; not a publicly released product. The design preview in `previews/` is illustrative, not a screenshot of the running application. The Windows installer is not precompiled in this source package.

## If you just want to test a Windows `.exe` installer

The goal is `Velomux-Setup-0.2.1-preview-Win-x64.exe`. A built installer contains the standalone `Velomux.exe` app and bundled `ffmpeg.exe`/`ffprobe.exe`, so installing and using it does **not** require Python, Inno Setup or a separate FFmpeg installation.

There are two ways to generate the installer:

**Local Windows builder:** If your computer has Inno Setup 7, FFmpeg (with ffprobe) and Python 3.11 or later **for building only**, extract the source archive and double-click **`BUILD_INSTALLER.cmd`**. It compiles the GUI using PyInstaller, then compiles the installer using your installed Inno Setup 7. Find the resulting setup EXE in `dist\installer\`.

**GitHub Actions Windows builder (no local Python needed):** In the official admknight/Velomux repository, run the manually triggered workflow **`Build Windows test installer`**. It uses a Windows runner to create a test setup and attaches it as a workflow artifact. Nothing is published to GitHub Releases by this preview workflow.

Read [Windows installer instructions](docs/BUILDING_INSTALLER.md) before building. On Windows 11 ARM64, the x64 installer may run under emulation; native ARM64 support is not validated.

## Features currently implemented

- Windows desktop Qt 6 GUI with a dark workstation-style interface, drag-and-drop, Quick / Advanced modes, searchable queue and per-item presets.
- Batch audio/video conversions using FFmpeg with observable progress and cancellation.
- Image conversion with Pillow; available codecs depend on included libraries.
- Video containers and presets: MP4 (H.264, H.265, AV1), MKV, MOV (ProRes), WebM (VP9/AV1), GIF and stream-copy/remux.
- Audio presets: M4A/AAC smart copy, M4A/ALAC, MP3, WAV, FLAC, OGG, Opus.
- Image outputs: JPG, PNG, WebP, TIFF, BMP, GIF, AVIF (when compiled Pillow support permits).
- Existing output controls: skip verified, repair corrupted/short/0-byte outputs, overwrite, or save numbered copies.
- Temporary output staging and validation before replacing a prior output; original inputs never changed.
- User-initiated GitHub update check (not configured until an official repository exists); no silent update installs.

**Not currently implemented:** Every conceivable format, RAW image processing, DVD/Blu-ray authoring, subtitle OCR/editing, LUT/HDR grading, hardware encoder UI, full video editor timeline, unattended updates, signed app/FFmpeg auto-updater, and parallel workers. Format/codec support is constrained by the actual FFmpeg/Pillow binary build.

## Project layout

- `modern_app.py` — Qt GUI, themes, batch and update center.
- `engine.py`, `toolchain.py` — conversion logic and bundled FFmpeg lookup.
- `assets/velomux.ico`, `assets/velomux.png` — product identity and Windows icon.
- `scripts/build_windows.ps1` — Windows private test build and checks.
- `installer/Velomux.iss` — Inno Setup 7 installation/uninstallation script.
- `BUILD_INSTALLER.cmd` — double-click build entry point for Windows.
- `.github/workflows/build-windows-installer.yml` — opt-in Windows CI builder for test artifacts.
- `tests/` — integration tests and basic static packaging checks.

## Source development (not required for installing Velomux)

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run.py
```

For frozen Windows builds, Velomux looks for bundled FFmpeg first and will work without separately installing it. Source development can fall back to a system FFmpeg installation.

## Open-source and licensing status

This code is intended for open-source distribution, **but the application license has not yet been approved**. Do not redistribute as an open-source release until the license is selected, FFmpeg binary provenance and corresponding source obligations are addressed, Qt/Pillow/Python notices are complete, and Windows runtime/installer testing succeeds. See `THIRD_PARTY_NOTICES.md` and `docs/RELEASING.md`.

A private local preview compiled from your own FFmpeg installation is **not cleared for public redistribution** merely because the build succeeds.

## GitHub builds and verified update workflow

The Windows-hosted GitHub Actions pipeline now includes an offscreen smoke test of the **actual Qt main window** before and after PyInstaller packaging, plus automatic silent installation, installed-executable testing and uninstallation of the real Inno Setup installer. Test artifacts include SHA-256 hashes and build provenance. This strengthens QA but does not substitute for independent clean-machine or conversion testing.

See [GitHub builds and updates](docs/GITHUB_BUILDS_AND_UPDATES.md) for the two build channels: short-lived **test artifacts** and a manually gated **draft GitHub Release**. Public release automation intentionally fails until an official repository, approved license and vetted FFmpeg source/hashes are provided. The running application's Update Center remains an opt-in check and does not silently replace FFmpeg or other executables.
