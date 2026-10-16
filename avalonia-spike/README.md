# Velomux Avalonia UI — nonshipping feasibility evaluation

Project Creator & Lead Maintainer: Adam Knight (@admknight).

This is a deliberately narrow, **real** technical proof of concept, not the production Velomux app. The existing Python / Qt project and installer on main remain untouched.

## What works in the evaluation source

A single end-to-end path is implemented: add files, choose M4A (AAC 192 kbps) or MP3 (192 kbps), select a destination, start FFmpeg extraction, check the resulting stream using ffprobe, surface errors, and cancel safely. New outputs are staged and never overwrite existing files or modify originals. A separate queue region and a single settings scroll area replace the nested scrollbars and wheel-driven tabs reported in the Qt interface.

## Explicit limits

- Only audio extraction is implemented in this spike. Other VeloFlow functions have **not** been ported and should not be advertised as working here.
- The Windows artifact is an **engineering test executable**, not an installer or public release. It currently requires FFmpeg and ffprobe in its folder or developer PATH. It does NOT bundle FFmpeg yet.
- There is no automatic updating, no signed setup, no whole-app feature parity, and no approval based on automated compilation alone.
- Validation checks for a readable audio stream but still requires the original engine's stronger contract and real-world regression corpus before replacing the shipping path.

## Running it from source

Install the .NET 10 LTS SDK. From the repository root:

    dotnet restore avalonia-spike/Velomux.Desktop/Velomux.Desktop.csproj
    dotnet run --project avalonia-spike/Velomux.Desktop/Velomux.Desktop.csproj

The dedicated GitHub workflow builds Windows and Linux, publishes a self-contained Windows evaluation binary, and never creates a public GitHub Release. Please do not treat this as a finished media-converter product.

## Acceptance before a main-branch migration

1. Confirm native Windows screenshots at 1280x720, 1600x900 and 1920x1080 and Windows DPI scaling at 100/125/150/200 percent; verify focus, legible text, no clipping or nested scrollbars.
2. Test repeated scrolling over settings and task/profile controls without any unintended changes.
3. Test with the user's actual MP4 audio files including long Unicode filenames, AAC/MP3 output and cancellation; repair the existing conversion-validation defects in the authoritative media layer.
4. Migrate the original seven task families and approved presets, media inspector, activity log, updates, folder workflows, permissions, and installer without dead controls or regressions.
5. Package actual hash-pinned FFmpeg and ffprobe binaries, verify codec capability, third-party license notices, install/upgrade/uninstall, and safe rollback before public distribution.
6. Preserve working Qt production branch until executable real-world parity is proven.

See the source-grounded architecture and acceptance review in docs/GUI_AUDIT_AND_AVALONIA_FEASIBILITY.md.
