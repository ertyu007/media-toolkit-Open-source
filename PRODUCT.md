# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

delegated: static single-file HTML/CSS/JS in `docs/`, served by GitHub Pages (no build step, no framework).

## Users

Thai-speaking Windows 10/11 users who want to convert, trim, or download media locally without accounts or cloud uploads; developers evaluating the open-source project.

## Product Purpose

Clipora is a local-first Windows media toolkit: extract audio, convert video, trim clips, download authorized public media, and separate stems. Success means a visitor understands the offer and downloads the right build without reading a manual.

## Positioning

Everything runs on the user's machine with FFmpeg, yt-dlp, and Demucs; sources are never modified, outputs are verified, and the app is Thai-first with a self-updater and CLI.

## Operating Context

Visitors arrive from GitHub Releases or the Pages site on desktop or phone, usually to grab the Setup or portable ZIP, check system requirements, or confirm that downloading public links is in scope.

## Capabilities and Constraints

- Audio extraction: MP3, M4A, WAV, FLAC, OPUS.
- Video: MP4 (H.264/AAC), MOV ProRes 422, hardware encode (NVENC/QSV/AMF), trim, FPS choice.
- Public URL downloads: single items, queued one at a time, via yt-dlp; no playlists, live, private/paid media, login, cookies, or DRM bypass.
- Stem separation with Demucs (offline after ~209 MB tool install), packed as `_stems.zip`.
- Headless CLI (`python -m clipora.cli`) with `--json` and exit codes.
- History with trash and retention; in-app updater verifies SHA-256.
- Version 0.7.2; Windows installer ~250 MB bundles Python, FFmpeg, yt-dlp, and Deno.
- GPL-3.0-only. No accounts, ads, telemetry, or cloud upload.

## Brand Commitments

Name: Clipora. Voice: direct, formal Thai; no hype or emoji. Existing app theme is Midnight Amethyst (charcoal + violet accent). The project is free and open source.

## Evidence on Hand

Repository docs: `README.md`, `docs/USER_GUIDE.md`, `docs/TROUBLESHOOTING.md`, `docs/CLI.md`, `docs/DEVELOPMENT.md`. Version source: `clipora/__init__.py`. No real screenshots, testimonials, benchmarks, or customer logos are available; do not fabricate them.

## Product Principles

1. Nothing leaves the machine; sources are never modified.
2. Show the work: verified outputs and honest limits, not marketing claims.
3. Thai-first copy with plain, formal wording.
4. Fast path first: download, install, pick a file or link, start.

## Accessibility & Inclusion

Thai text must remain readable at mobile sizes; respect reduced-motion preferences; keep keyboard focus visible.
