# Building a Velomux test installer (Windows / Inno Setup 7)

## What is installed on the testing user's PC?

A single `Velomux-Setup-0.3.0-preview-Win-x64.exe` installer, containing:

- `Velomux.exe` and its frozen Python/Qt/Pillow runtime (not a Python source launcher).
- `ffmpeg.exe` and `ffprobe.exe` bundled inside the app directory.
- Start-menu entry, optional desktop shortcut and Inno Setup uninstaller.

**No separate Python, FFmpeg or Inno Setup is required for the person installing and using the EXE.** The build computer, by contrast, needs build dependencies.

## Local build on Windows (build computer only)

1. Extract the source ZIP anywhere, keeping the folder hierarchy intact.
2. Confirm **Inno Setup 7** is installed. The script checks standard and per-user locations (including `%LOCALAPPDATA%\Programs\Inno Setup 7\ISCC.exe`) and the `ISCC.exe` command. It verifies the compiler using `ISCC.exe /?`, not the Windows file-version metadata, which can return 0 for valid ISCC builds.
3. Confirm **FFmpeg and ffprobe** resolve in PowerShell: `ffmpeg -version` and `ffprobe -version`.
4. Confirm build-only Python 3.11+ is available via `py -3 --version` or `python --version`.
5. Double-click `BUILD_INSTALLER.cmd`. It runs tests, freezes the app with PyInstaller, verifies that bundled binaries exist and pass a self-test, then calls Inno Setup 7.
6. The resulting installer (if successful) appears in `dist\installer\Velomux-Setup-0.3.0-preview-Win-x64.exe`.

If Inno Setup was installed in a custom folder, set `VELOMUX_ISCC_PATH` to its `ISCC.exe` file before starting `BUILD_INSTALLER.cmd`, or pass `-InnoSetupCompilerPath "C:\path\to\ISCC.exe"` to `scripts\build_windows.ps1` directly. Neither is necessary for typical per-user installations.

If Python is not installed and you do not want to install build tools locally, use the GitHub-hosted build below.

## GitHub Actions alternative (no local Python/Inno build tools)

After you explicitly approve creating a GitHub repository and upload this project's source, open **Actions → Build Windows test installer → Run workflow**. Download the resulting private test artifact from that workflow run. The CI runner needs to have Inno Setup 7 and ffmpeg; any missing build tool causes a visible failed workflow, not a misleading fake installer. The workflow does not create public Releases automatically.

## Testing checklist

1. Run the installer on Windows 10/11 x64 with no Python installation required.
2. Open the app from the Start menu, and confirm the update/about page does not use an old project name.
3. Confirm the engine indicator says **Bundled FFmpeg** with the PC's existing PATH FFmpeg removed/renamed temporarily, or on a fresh test machine without FFmpeg.
4. Convert MP4→M4A, MP3→FLAC, PNG→WebP and MP4→MP4 on sample files.
5. Cancel a conversion, then retry. Test existing valid, 0-byte and corrupt outputs; ensure original files remain unchanged.
6. Uninstall. Confirm only app-installed files and shortcuts were removed, not your source media or converted output files.

The build script runs an automatic frozen-EXE smoke test, but it does **not** replace interactive Windows GUI and install/uninstall testing. No Windows graphical or installer test has yet been performed in the present Linux environment.

## Distribution warning

`-UseSystemFFmpeg` copies local binaries for *private test builds*. Before sharing an installer publicly, select a source-code license, inventory redistributable Qt/Python components, verify exactly which FFmpeg build is bundled, and meet its license/source distribution obligations. `-ForDistribution` checks a subset of these conditions, but is not legal approval or a security review.

### Extra verification added to Windows CI

The release build now runs `run.py --gui-smoke-test` with `QT_QPA_PLATFORM=offscreen` before and after freezing. This constructs, navigates, displays, and closes the actual PySide6 main window rather than only importing `PySide6.QtWidgets`. Failures write `Velomux-GUI-Smoke-Test.log` under `%TEMP%` for diagnosis.

When using Chocolatey's FFmpeg package, the build script resolves the **real binary pair**, not Chocolatey launch shims. The explicit `-FFmpegBinDirectory` option can be used for reviewed local test executables. The GitHub test workflow then runs `scripts/test_installer_windows.ps1` against the compiled setup and emits checksums/provenance. None of this requires Python on the end user's machine.

The separate draft-release workflow is gated by a vetted FFmpeg archive manifest, full licensing work and human approval. See [GitHub builds and updates](GITHUB_BUILDS_AND_UPDATES.md).
