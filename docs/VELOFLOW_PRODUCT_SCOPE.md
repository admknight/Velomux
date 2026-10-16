# VeloFlow: curated Velomux media workstation roadmap

**Product**: Velomux (independent open-source media utility in development)
**Project Creator & Lead Maintainer**: Adam Knight ([admknight](https://github.com/admknight))
**Principle**: learn *interaction patterns* from established tools; ship original
Velomux UI, naming, implementation, code, and assets. No third-party project
branding or proprietary visual/source assets are included.

## What is actually implemented in this development branch

| Inspiration | Velomux interpretation | Implementation | Proof |
| --- | --- | --- | --- |
| HandBrake's purpose-oriented profiles | **VeloFlow** task picker and purpose-based formats | 7 workflows, 29 descriptions mapped to actual engine presets (video, audio, images, extraction, compression, rewrap, trim) | `tests/test_veloflow_catalog.py`, Qt UI tests |
| Shutter Encoder's function browser | **VeloFlow actions** instead of hiding conversion, extraction, remux and cut options in codec menus | Audio extraction, video/audio/image conversion, trim and stream-copy rewrap via existing FFmpeg engine | GUI and integration tests |
| File Converter's Explorer workflow | **Open in Velomux** optional per-user Explorer verb | Inno Setup opt-in `explorercontext`; file launched into queue, never auto-converted | Silent install/uninstall registry smoke test |
| MediaHuman's batch workflow | **Album/folder-conscious Smart Queue** | Mixed media recommendation by input kind, preserved relative folders when importing directories into a custom destination | Destination and GUI import tests |
| LosslessCut's fast stream ops | **Safe Rewrap / Keyframe Trim** | Stream copy keeps compatible video/audio/subtitle tracks; optional keyframe-aligned trim; accurate trim re-encodes | FFmpeg multi-track remux integration tests |

An existing output is not overwritten until the newly generated temp file
passes validation; errors now identify the exact failed check. A full media
workstation remains a *product goal*, not the currently achieved release status.

## Specific follow-on capabilities still required

| Capability | Status | Acceptance before labeling 'supported' |
| --- | --- | --- |
| Accessible purpose/device/resolution profiles | Partial: purpose-based | Device profiles tested for expected codecs, max resolution and frame rates |
| Stream/track browser (choose/remove/replace multiple tracks) | Not implemented | Explicit stream maps, subtitle/container compatibility, multitrack regression |
| Audio waveform, thumbnails, timeline and visual cut preview | Not implemented | Native GUI renders real sampled waveforms and keyframe/cut feedback; no fake preview |
| Frame-accurate cutting and multiple labeled segments | Partial: one trimmed range can re-encode | Compare output frames/cut boundaries against selected points |
| Watch folders and custom file renaming from tags | Not implemented | Stable-file detection, safe filename tokens, cancellation, tests |
| CUE splitting, metadata-based filenames and music archive tools | Not implemented | Preserve album/artist/title tags and directories, valid CUE regression corpus |
| Export encoder capability matrix + hardware acceleration | Not implemented | Probe binary encoders/muxers, probe GPU at runtime, hide unsupported profiles |
| File Explorer multi-selection in *one* queue | Partial: each Explorer verb may launch a separate instance | Single-instance IPC/queue integration, Unicode paths, Windows 11 menu tests |
| Compression quality preview and estimated output size | Not implemented | Estimates labeled approximate; source-level comparisons + QA |
| Parallel conversion workers and reliable pause/resume | Not implemented | Bounded scheduling, cancellation, no file truncation/race, stress tests |
| Signed app/setup and safely verified updates | Not implemented | Code signing, checksum/provenance, rollback, legal review |

## Current release blockers

1. Real-world MP4-to-M4A validation failures reported on the user's Windows PC
   are not yet reproduced from those exact media files. The next build exposes
   validation mismatch reasons, but that is **not a verified fix**.
2. Changing bitrate/quality while using the existing 'repair/skip verified'
   policy can mistakenly treat an older successful output as a match for a
   different preset. See the linked GitHub correctness issue.
3. Visual GUI acceptance requires native Windows desktop review; offscreen
   runner screenshots alone are not proof of rendering quality.
4. The application license, third-party redistribution notices, public
   installer signing, and automatic update safety have not cleared release.

**Do not claim parity with HandBrake, Shutter Encoder, File Converter,
MediaHuman or LosslessCut on the basis of a preset count or a passing installer.**

## External functionality references

- https://handbrake.fr/docs/en/latest/technical/official-presets.html
- https://www.shutterencoder.com/documentation/
- https://file-converter.io/
- https://www.mediahuman.com/audio-converter/
- https://github.com/mifi/lossless-cut

These links document feature inspirations, not copied source or endorsed branding.
