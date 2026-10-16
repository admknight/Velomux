# Third-party software / release compliance tracker

This file records known components and distribution obligations; it is **not** by itself a completed compliance package.

## FFmpeg / ffprobe

Project: https://ffmpeg.org/  |  Source: https://git.ffmpeg.org/ffmpeg.git  |  Licenses: LGPLv2.1+ by default, GPL when enabled build components are included; a build may be under GPLv3 depending on its configured libraries. See https://ffmpeg.org/legal.html. Do not infer binary licensing from the filenames alone. Record the actual release binary source URL, SHA-256, build configuration, license variant, source commit and corresponding source-access obligations in `vendor/ffmpeg/BINARY_MANIFEST.json`, `vendor/ffmpeg/PROVENANCE.md` and `vendor/ffmpeg/SOURCE_OFFER.md` before public distribution.

## Qt for Python / PySide6

https://www.qt.io/development/qt-framework/python-bindings  |  Available under LGPLv3/GPLv2/GPLv3 or a separate commercial license, subject to the license terms for modules actually used. Include applicable license texts, notices and obligations for packaging, library replacement, and any statically linked or redistributed Qt pieces.

## Pillow

https://python-pillow.github.io/  |  PIL Software License (Historical Permission Notice and Disclaimer). Include its license and corresponding third-party notices in public releases.

## Python / PyInstaller dependencies

Any redistributed runtime, Qt modules/plugins, codecs and build dependencies must be inventoried in release SBOM and reviewed for attribution and obligations. Publishing code under an open-source license does not automatically satisfy bundled-binary compliance.
