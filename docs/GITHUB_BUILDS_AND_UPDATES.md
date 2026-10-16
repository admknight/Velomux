# Velomux: GitHub builds, installers, and future updates

**Current scope:** Windows x64 test/release-candidate builds. The installer has not yet been built and tested from these workflows. Users of successful standalone builds do **not** install Python, PySide6, FFmpeg, or Inno Setup separately.

## How ordinary users receive Velomux

- GitHub Actions runs on a **Windows** hosted virtual machine, installs Python/PySide6/PyInstaller only for compilation, and bundles the Python runtime, Qt plugins, conversion app, Pillow, and `ffmpeg.exe`/`ffprobe.exe`.
- The frozen folder contains `Velomux.exe` (the actual launcher); Inno Setup 7 then packages that frozen folder into one setup EXE. The installed app operates offline for local media conversion.
- A conventional Windows application needs Windows-compatible system DLLs; a separate Python installation is *not* one of its dependencies. A clean Windows 10/11 x64 runtime test is required before a public release. An unsigned test installer can trigger SmartScreen warnings.

## Channel 1: Build a **private test installer** in GitHub Actions

1. Create a GitHub repository and upload the Velomux source, keeping `.github/workflows/`, `scripts/`, `installer/`, and the root files intact. No `dist/`, `.venv/`, local binaries or secrets need to be committed.
2. Open **Actions > Build Windows test installer > Run workflow** on the desired branch.
3. The Windows runner installs a build-only Python 3.12, test-only FFmpeg, and signature-verified Inno Setup 7.1.0, then performs source tests and constructs the actual Qt UI offscreen.
4. PyInstaller creates `Velomux.exe` with bundled dependencies. The workflow runs two checks against this **frozen executable**: its tool/asset self-test and actual GUI-window creation.
5. Inno Setup creates `Velomux-Setup-0.3.1-preview-Win-x64.exe`. CI silently installs it into a temporary folder, runs both tests against the **installed** copy, and uninstalls it.
6. After all gates pass, **Actions > the successful run > Artifacts** contains a test-installer ZIP with the setup EXE, portable ZIP, `SHA256SUMS.txt`, `BUILD_PROVENANCE.txt`, and actual Qt-window screenshots (`qt-gui-source.png` and `qt-gui-frozen.png`) for graphical review.

This test workflow has **read-only repository permissions**, and it cannot publish to GitHub Releases. Downloadable artifacts are retained for 14 days. An Actions artifact is **not** a publicly approved redistribution of the FFmpeg binary inside it.

## Channel 2: Stage a **reviewed draft GitHub Release**

**Not available until the release prerequisites below are actually satisfied.**

The separate workflow `.github/workflows/draft-release.yml` is manual, requires an **existing** Git tag matching `version.py`, and refuses to run unless the official `GITHUB_REPOSITORY` is set to the exact GitHub repository. It also requires `reviewer_confirmed`.

It expects checked-in and approved files:

- `LICENSE`: complete, chosen application license.
- `vendor/ffmpeg/BINARY_MANIFEST.json`: JSON with `binary_source_url` (HTTPS ZIP), `archive_sha256`, `ffmpeg_sha256`, `ffprobe_sha256`, `source_revision`, and `license_variant`.
- `vendor/ffmpeg/PROVENANCE.md`: verified FFmpeg build origin/configuration and exact version.
- `vendor/ffmpeg/SOURCE_OFFER.md`: reviewed distribution/source-compliance arrangement.
- Appropriate additional Python/Qt/Pillow/FFmpeg notices and relevant license terms.

The staging script downloads only the manifest-pinned HTTPS ZIP and compares its archive and executable SHA-256 hashes. The builder also checks the staged pair and required disclosure files. **These automated checks do not provide legal clearance or software-signing guarantees.**

When all prerequisites, Windows EXE tests, actual install/uninstall test, and asset hash checks pass, the workflow creates a **DRAFT, prerelease GitHub Release**, not a published release. A maintainer must separately inspect the release and publish it. GitHub itself provides downloadable source ZIP/TAR archives for a release tag; the workflow attaches the Windows setup, portable ZIP and SHA-256 manifest.

## Updates: application and bundled FFmpeg

- **Current app:** The Update Center supports a user-triggered latest-GitHub-release *check*, but `version.py` has no official repository assigned yet. It does **not** automatically install updates.
- **Current FFmpeg:** Its version is shown in the Update Center. It is bundled into each setup build. FFmpeg is not independently downloaded or replaced in installed program folders.
- **Safe first public-update strategy:** Ship a reviewed installer that upgrades Velomux and its vetted FFmpeg binary pair together. This gives users normal uninstall/upgrade behavior and a testable rollback path. FFmpeg updates require codec regression testing and licensing/provenance revalidation.
- **Future separately updated FFmpeg:** would require a secure signed update manifest, trusted binary origin and hash verification, staging, rollback, elevation/permissions design and compatibility tests. This is intentionally **not implemented**; no silent binary execution/update is promised.

## Release gates that GitHub cannot certify by itself

- Complete third-party open-source redistribution review (FFmpeg optional GPL components, Qt/PySide6 licensing, Python/Pillow notices).
- Real Windows 10/11 x64 QA on machines without development tools, including common conversions, corrupted files, cancellation and reliable upgrade/uninstall.
- Code signing and installer reputation/SmartScreen experience, where required for the intended audience.
- Pinned Python dependency versions and reviewed changes before a stable reproducible release.

The GitHub workflows have been prepared as source. **They are not running, and they have not produced a verified Windows installer**, until a repository is created and the Windows jobs are executed successfully.
