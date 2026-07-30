# Clipora Product and UX Reference

## Contents

1. Product definition
2. Users, jobs, and non-goals
3. Current MVP
4. Canonical journeys
5. UI state model
6. Validation and errors
7. Output choices
8. Feature acceptance criteria
9. Accessibility and localization
10. Roadmap

## 1. Product definition

Clipora is a local-first Windows desktop tool for preparing media the user owns or may lawfully use. Its initial promise is: select a local video, extract useful audio or create a compatible MP4, monitor progress, and find the result without uploading the source or seeing ads.

Follow these principles:

- Process locally by default.
- Never modify the original.
- Present one clear next action.
- Distinguish remuxing, transcoding, and lossy conversion honestly.
- Keep failures recoverable without restarting.
- Show exact output location and meaningful progress.
- State intended use without pretending to decide legal rights.

## 2. Users, jobs, and non-goals

Primary user: a Thai-speaking creator or everyday Windows user with a local media file who wants audio or broadly compatible video without an ad-heavy web service.

Core jobs:

- Extract audio for editing, transcription, or personal reuse.
- Convert a local video to H.264/AAC MP4.
- Choose quality/size without codec expertise.
- Know whether the operation is working and where output went.

Non-goals:

- Full timeline editing.
- DRM or access-control bypass.
- Arbitrary protected/private-media downloads.
- Claims of lossless output when re-encoding.
- Hosting files or requiring accounts.
- Replacing professional nonlinear editors.

## 3. Current MVP

The current implementation provides single local-file selection, an existing destination folder, MP3/M4A extraction, H.264/AAC MP4 conversion, three CRF quality labels, progress from FFmpeg output time, overwrite confirmation, and optional folder opening.

Treat anything else as proposed until verified in code.

## 4. Canonical journeys

### Happy path

1. Launch and see the product promise and idle state.
2. Select supported local media.
3. Confirm/change destination.
4. Choose audio extraction or MP4 conversion.
5. Choose the contextual format/quality.
6. Start; observe busy state and progress.
7. Receive success naming the exact target.
8. Optionally open its folder.

### Recovery path

1. Start with missing, moved, unsupported, or invalid input.
2. Receive concise explanation at the action point.
3. Retain prior valid choices.
4. Correct only the invalid value and retry.

### Collision path

Compute target before starting, detect an existing path, ask before replacement or generate a new name, and never truncate existing data before explicit confirmation and job start.

## 5. UI state model

| State | Primary action | Inputs | Progress | Transitions |
|---|---|---|---|---|
| Idle | Enabled | Editable | 0/hidden | Validating |
| Validating | Disabled | Locked | Indeterminate | Running, Error |
| Running | Disabled | Locked | Determinate/indeterminate | Success, Error, Cancelling |
| Cancelling | Disabled | Locked | Frozen/indeterminate | Cancelled, Error |
| Success | Enabled | Editable | 100 | Idle, Validating |
| Error | Enabled | Editable | Intentional reset/preserve | Validating |
| Cancelled | Enabled | Editable | Reset | Validating |

Never leave the primary button disabled after handled failure. If cancellation is added, make its action unambiguous.

Preferred status copy:

- `พร้อมเริ่มงาน`
- `กำลังตรวจสอบไฟล์…`
- `กำลังประมวลผล… 42%`
- `กำลังยกเลิก…`
- `เสร็จแล้ว: filename.mp3`
- `ยกเลิกงานแล้ว`
- `แปลงไฟล์ไม่สำเร็จ`

## 6. Validation and errors

Validate in order:

1. Source value exists.
2. Source is a readable regular file.
3. Destination exists and is a directory.
4. FFmpeg and ffprobe are discoverable.
5. Operation values are supported.
6. Probe succeeds and required streams exist.
7. Collision policy is resolved.
8. Optional permission/capacity checks pass.

| Condition | User copy |
|---|---|
| No source | `กรุณาเลือกไฟล์วิดีโอก่อน` |
| Moved source | `ไม่พบไฟล์ต้นฉบับ กรุณาเลือกไฟล์ใหม่` |
| No audio | `ไฟล์นี้ไม่มีเสียงให้แยก` |
| No video | `ไฟล์นี้ไม่มีภาพวิดีโอสำหรับแปลง` |
| Missing FFmpeg | `ไม่พบ FFmpeg กรุณาติดตั้งแล้วเปิด Clipora ใหม่` |
| Invalid trim | `ช่วงเวลาสิ้นสุดต้องมากกว่าเวลาเริ่มต้น` |
| Destination denied | `ไม่สามารถเขียนไฟล์ในโฟลเดอร์นี้ กรุณาเลือกโฟลเดอร์อื่น` |
| Disk full | `พื้นที่จัดเก็บไม่เพียงพอ กรุณาเพิ่มพื้นที่หรือเปลี่ยนโฟลเดอร์` |
| Process failure | `แปลงไฟล์ไม่สำเร็จ กรุณาตรวจสอบไฟล์แล้วลองอีกครั้ง` |

Expose bounded technical detail for support; never dump an unbounded FFmpeg log into a modal.

## 7. Output choices

- MP3: widest consumer compatibility; lossy; use libmp3lame quality semantics.
- M4A: AAC in an MPEG-4 audio container; lossy; good quality/size.
- High: H.264 CRF 18.
- Balanced: CRF 23.
- Small: CRF 28.

Quality labels describe encoder targets, not recovery of missing source quality. If adding `Original`, define whether it means compatible stream copy/remux; never use it as a synonym for high-bitrate transcoding.

Naming must preserve the useful source stem, add a stable operation suffix, use the actual extension, handle Windows-invalid/reserved names, resolve collisions, and never surprise the user by changing destination.

## 8. Feature acceptance criteria

### Audio extraction

- Produce playable audio in the chosen format from a file with audio.
- Exclude video streams.
- Explain missing audio.
- Keep expected duration within container/encoder tolerance.
- Preserve source bytes.

### MP4 conversion

- Produce H.264 video and AAC audio when present.
- Handle silent video intentionally.
- Respect quality mapping.
- Require successful finalization before reporting success.
- Never label re-encode as lossless.

### Trimming

- Accept a documented time format and normalize it.
- Reject negative, reversed, equal, and out-of-range intervals.
- Use effective clip duration for progress.
- Define seek accuracy/keyframe trade-offs.
- Preserve A/V synchronization.

### Batch processing

- Show each job, state, and target.
- Define continuation after failure.
- Avoid cross-job target collisions.
- Define current/queued cancellation.
- Compute aggregate progress safely with unknown durations.

### Presets

- Store presets as data.
- Display intended use and constraints.
- Define fit/crop/pad, frame rate, codecs, and audio behavior.
- Do not claim official certification or guaranteed upload acceptance.

## 9. Accessibility and localization

- Preserve keyboard navigation, visible focus, and sensible tab order.
- Never communicate state through color alone.
- Maintain readable contrast in normal/disabled states.
- Avoid fixed sizing that clips Thai at common Windows scale factors.
- Manually check 100%, 125%, and 150% after layout changes.
- Keep Thai natural; retain technical terms where translation harms clarity.
- Centralize strings before adding another language.

## 10. Roadmap

Prioritize:

1. Harden single-file conversion.
2. Add cancellation and exact incomplete-output cleanup.
3. Add stream-aware validation and clearer errors.
4. Add trimming.
5. Add collision-free names and recent destination.
6. Add batch processing.
7. Add export presets.
8. Package/test a Windows executable.
9. Explore authorized imports as a separate capability.

Do not let a broad “download everywhere” promise displace reliability of the local conversion core.
