# Architecture and feature coverage

`modern_app.py` is the Qt 6 GUI; `app.py` is the preserved legacy Tk fallback; both share the same `engine.py`. `toolchain.py` resolves the vetted bundled binary directory before developer PATH. `run.py` launches Qt. `cli.py` supports scripted batch jobs. `version.py` is the single source of version and update-channel identity.

A single QThread sequentially runs the conversion queue, posting status, progress and completion events to the GUI event loop. It can be cancelled; FFmpeg operations terminate on cancellation. The conversion engine writes to a temporary file on the same volume as its final output and validates before atomic replace. When collision policy is repair, complete outputs are skipped and zero-size, truncated or incorrectly formatted outputs are reconverted. Optional full-decode validation catches additional stream corruption.

**Limitations:** duration validation allows a tolerance based on media container. Advanced image color metadata and variable-frame-rate edge cases need further qualification. Existing-file verification can never prove two media files are semantically identical. Conversion options apply batch-wide; output preset can differ per queued source. The UI currently offers a single worker, no arbitrary FFmpeg CLI injection, no live waveform preview, no concurrent task scheduling and no silent binary updates.

**Security considerations:** tools are invoked through argument arrays, not shell interpolation; filenames are passed as paths, not parsed as shell commands; app does not invoke arbitrary downloaded binaries or upload user files. For public distribution, pin binary hashes, verify releases and expose provenance transparently. Full sandboxing and hostile file parser containment are not currently implemented.

## Qt main-window and packaging smoke test

`run.py --gui-smoke-test` constructs `modern_app.MainWindow` using Qt's offscreen platform in CI, checks the four navigation pages, conversion queue, advanced tabs and Quick/Advanced mode behavior, and opens/closes the window. This test is executed with the source program, the frozen Windows EXE and the copy installed by the real Inno Setup installer. The ordinary user does not need a Python/PySide6 installation: the frozen application includes those dependencies. The smoke test is not a full UI automation or media-conversion acceptance test.
