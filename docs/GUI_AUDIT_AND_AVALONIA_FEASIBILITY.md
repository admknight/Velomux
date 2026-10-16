# Velomux GUI audit and Avalonia feasibility — 2026-10-17

**Status:** SOURCE-AND-USER-SCREENSHOT AUDIT ONLY. No native Windows visual acceptance is claimed. This branch is a reversible migration evaluation, not the release branch.

## Evidence

- The user supplied four real Windows screenshots of the `0.3.1-preview` Qt settings workspace showing clipped content, nested vertical scrollbars, dark/empty tab space and scroll-wheel tab switching.
- `modern_app.py` has a single `MainWindow` composing navigation, queue, settings, activity, update and About pages and managing work state in one module (>1,500 lines).
- `modern_app.py` lines 531–618 construct a scrollable right-hand settings card, a `QTabWidget`, fixed minimum tab height and a mode toggle. Lines 767–780 create an *additional* `QScrollArea` within *each* tab page.
- `modern_app.py` lines 113–168 protect `QSpinBox`, `QDoubleSpinBox` and `QComboBox` from wheel changes but do **not** protect `QTabBar`; Qt's bar can change tabs on wheel events.
- `run.py` GUI smoke tests check widgets exist, switch pages and capture an offscreen Qt screenshot, but do not detect contrast, clipping, nested scroll-area layout or mouse-wheel tab changes. The CI offscreen screenshots previously had illegible square glyphs.
- Existing actual conversion failures (including output-validation errors on music MP4 files) are **separate engine defects**; a new UI toolkit cannot fix them automatically.

## Root cause and corrective design

| Symptom | Cause / evidence | Required acceptance |
| --- | --- | --- |
| Inner and outer scrollbars | Right settings panel wraps tab pages that each have independent scroll areas | Exactly one vertical settings scroll container; queue has separate *non-nested* scrolling |
| Wheel changes tabs | `QTabBar` has no wheel guard | Scrolling with pointer on tab strip never changes selected settings; use click/keyboard only |
| Large black blank fields | `QTabWidget` minimum height 270, inner widget backgrounds and hard-coded style | No forced unused pane height; only visible sections consume vertical space |
| Cramped Quick Mode | An advanced tab widget still appears in Quick Mode, with technical settings below task buttons | Quick Mode shows a compact basic-settings section; Advanced settings use task-scoped expandable groups |
| Non-responsive settings | Fixed sidebar / minimum widths / two-column task grid with no breakpoint rules | No clipping at 1280x720, 1600x900, 1920x1080; support 100/125/150/200% scale |
| Invisible GUI regressions | Build passes widget construction without native rendered inspection | Native Windows screenshots and interaction tests are release gates; CI glyphs must be legible |
| Hard-to-maintain UI | Large stateful monolith combines presentation and conversion orchestration | Views, view-models, queue services and FFmpeg process layer independently testable |
| Confusing conversion statuses | User saw 100% complete while every job failed | Progress distinguishes finished attempts and valid successes, plus conspicuous failure states |
| Trust/authorship | Creator role and third-party licenses must be visible/consistent | Project Creator & Lead Maintainer Adam Knight; third-party notices and versions remain visible |

## Migration choice: Avalonia UI

Use **Avalonia 12.1.x (MIT-licensed core) and .NET 10 LTS (supported through November 2028)** with C# and XAML, MVVM, and .NET self-contained publishing. This is a qualified recommendation; availability of premium designer tools is NOT a framework requirement.

**Candidate architecture**

- `Velomux.Desktop`: Avalonia/XAML views + Fluent styling, responsive Grid, navigation and accessibility.
- `Velomux.Application`: task/profile view-models, queue, cancellation, presets, settings and event history.
- `Velomux.Media`: FFmpeg/ffprobe process wrappers, stream metadata, codec/container validation, argument arrays (never an interpolated shell command), output staging and verification.
- `Velomux.Tests`: independent conversion contract tests, UI control behaviors and Windows integration tests.
- `installer`: retain Inno Setup 7, signed public build gated separately; package self-contained .NET app with separately staged bundled FFmpeg tools.

There are **two** safe migration strategies:
1. **Preferred end-state**: Port the conversion orchestration to a C# process service using bundled FFmpeg binaries (no Python dependency for end users). Require parity tests against the old Python engine before changing the default application.
2. **Short-term bridge**: Bundle frozen Python engine out of process and use a narrow local JSON/IPC contract from Avalonia. Lower conversion rewrite risk, but larger installer and dual runtime. Only useful as a temporary compatibility bridge.

Do **not** try to embed Python source directly in C#. Do not retire the PySide6 app until a real Windows installer, FFmpeg conversion corpus, upgrade/uninstall, and native visual acceptance all pass.

## Non-negotiable release gates

- UI: Verify screenshots & interactions on a native Windows 10/11 desktop at 1280x720, 1600x900, 1920x1080, and Windows scaling 100%, 125%, 150%, 200%.
- A single scroll region per settings workspace; no nested tabs with wheel-driven selection; controls remain usable via keyboard/touch/mouse.
- No status/format setting may change when scrolling over a non-activated field.
- File queue, seven VeloFlow actions and all existing user-approved profiles must be truly functional; no decorative buttons.
- Run an end-to-end corpus covering MP4→M4A, MP3, video/transcode, image, remux with multitrack audio and subtitles, long Unicode names, zero-byte/partial-output repair, collision with changed presets, cancellation, trim accuracy and preserving originals.
- Installed app must report actual FFmpeg version, reject incompatible codecs up front and preserve originals until verified output completion.
- No release without license/legal checks for the actual FFmpeg build, Qt/Python dependencies if bundled, new Avalonia packages and runtime.
- Automatically test .NET self-contained Windows x64 publish, Inno Setup install/upgrade/uninstall, hash provenance, and no end-user .NET/Python prerequisite.
- No claim of production readiness from `dotnet build` or headless smoke tests alone.

## Decision boundaries

Create an Avalonia proof of concept in this *separate branch*. Build/run the real UI with one vertically integrated conversion workflow and a native Windows screenshot review; then compare with current Qt on usability, CPU/RAM, package size and regression coverage. Only then decide whether to migrate the app's default GUI. No changes to the `main` Qt app are authorized merely by this audit.
