# คู่มือพัฒนา Clipora

## สารบัญ

1. เป้าหมายและ stack
2. เตรียม environment
3. Architecture
4. Thread และ subprocess rules
5. Workflow การเปลี่ยนโค้ด
6. Testing
7. เพิ่ม format หรือ feature
8. Documentation และ release readiness

## 1. เป้าหมายและ stack

Clipora เป็น local-first Windows desktop media toolkit สำหรับไฟล์ที่ผู้ใช้มีสิทธิ์ใช้

- Python 3.10+
- Tkinter/ttk
- External FFmpeg และ ffprobe
- Standard-library unittest
- ไม่มี runtime Python dependency ภายนอกในปัจจุบัน

รักษา source safety, UI responsiveness, Unicode paths, bounded diagnostics และ explicit stream behavior ก่อนเพิ่ม feature

## 2. เตรียม environment

```powershell
git clone https://github.com/ertyu007/media-toolkit-Open-source.git
cd media-toolkit-Open-source
python scripts/check_environment.py
python -m unittest discover -s tests -v
python app.py
```

ไม่จำเป็นต้องสร้าง virtual environment ในรุ่นที่ไม่มี dependency แต่สามารถสร้างเพื่อแยก Python tooling:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

อย่าเพิ่ม package ลง `requirements.txt` เพียงเพื่อ development convenience โดยไม่แยก runtime/dev requirement และอธิบายเหตุผล

## 3. Architecture

```text
app.py
  -> CliporaApp (clipora/ui.py)
     -> snapshot JobSpec หรือ ImportSpec on Tk main thread
     -> worker thread
        -> local: probe -> build_command -> FFmpeg
        -> URL: validate_url -> build_import_command -> yt-dlp/FFmpeg
     <- after callbacks for progress/success/failure
```

### `app.py`

Entry point เท่านั้น อย่าใส่ business logic

### `clipora/ui.py`

รับผิดชอบ widgets, dialogs, display copy, validation เบื้องต้น, immutable job snapshot และ terminal UI states ห้ามใส่รายละเอียด codec/progress protocol ที่ควรทดสอบแบบ pure function

### `clipora/ffmpeg.py`

รับผิดชอบ model ปัจจุบัน, tool discovery, ffprobe JSON, stream validation, output naming, argument construction, progress parsing และ process runner

เมื่อ module โต ให้แยกตาม responsibility เป็น models/media/commands/runner/naming โดยไม่ทำ refactor ใหญ่พร้อม feature ที่ไม่เกี่ยวข้อง

### `clipora/importer.py`

รับผิดชอบ URL validation, yt-dlp และ Deno/Node discovery, safe argument construction, progress protocol, single-item download, collision-free finalization และ job-owned temporary directory ห้ามเพิ่ม cookies, credentials, login, private media หรือ DRM bypass โดยไม่มี product/security review ใหม่

## 4. Thread และ subprocess rules

- สร้างและอ่าน Tk widgets/variables บน main thread เท่านั้น
- Snapshot `JobSpec` ก่อนเริ่ม worker
- Probe และ encode ใน worker
- ส่ง UI update ผ่าน `after` หรือ queue ที่ main thread poll
- ใช้ subprocess argument list และ `shell=False`
- ซ่อน FFmpeg console บน Windows
- อ่าน pipe แบบไม่ deadlock และเก็บ diagnostic tail แบบ bounded
- Success ต้องมี exit code 0 และ target ที่มีขนาดมากกว่า 0
- Source ห้ามเป็น cleanup target
- การเพิ่ม cancel ต้องถือ process handle ที่แน่นอน ห้าม kill ตามชื่อ process
- URL import ต้องหยุด exact yt-dlp process tree เพราะ yt-dlp อาจเรียก FFmpeg เป็น process ลูก
- ใช้ `--ignore-config` เพื่อไม่รับ credential/cookie/exec options จาก config ส่วนตัวโดยไม่ตั้งใจ

## 5. Workflow การเปลี่ยนโค้ด

ทำเป็น vertical slice:

1. เขียน outcome และ acceptance criteria หนึ่งเรื่อง
2. ระบุ modules และ non-goals
3. แก้ pure function/model ที่เล็กที่สุด
4. เพิ่ม unit test
5. เชื่อม core process และเพิ่ม generated-fixture integration test
6. เชื่อม UI หลัง core ผ่าน
7. ทดสอบ manual interaction ที่เกี่ยวข้อง
8. อัปเดต docs

สำหรับ bug ให้นำ exact error/traceback/exit code/diagnostic tail มาจำแนก layer ก่อนแก้ เพิ่ม regression test และเปลี่ยน causal hypothesis ทีละเรื่อง

## 6. Testing

รัน syntax/import:

```powershell
python -m compileall -q app.py clipora tests scripts
```

รันทุก test โดยยกระดับ ResourceWarning เป็น failure:

```powershell
python -W error::ResourceWarning -m unittest discover -s tests -v
```

กลุ่มหลัก:

- `test_ffmpeg.py`: naming, command, stream validation, progress
- `test_ffmpeg_integration.py`: FFmpeg จริงกับ temporary generated media
- `test_check_environment.py`: dependency checker ด้วย mocks
- `test_importer.py`: URL validation, safe yt-dlp arguments, progress, collision และ temp cleanup
- `test_tools.py`: managed/bundled/PATH discovery และ environment override
- `test_dependencies.py`: checksum, safe archive staging, cancellation และ install record

Integration test ต้อง:

- skip อย่างชัดเจนเมื่อไม่มี tools
- สร้าง fixture ใน temporary directory
- ไม่ใช้ media ส่วนตัว
- probe output ไม่ตรวจเพียง existence
- ยืนยันว่า source ไม่เปลี่ยนเมื่อเกี่ยวข้อง

Manual GUI checks ที่ unit test แทนไม่ได้:

- initial state และ mode switching
- dialog/error copy
- controls ระหว่างงานและหลัง failure
- progress visual
- overwrite prompt
- Thai text และ display scale 100/125/150%
- close ระหว่างงาน

บันทึกสิ่งที่ไม่ได้ทดสอบ ห้ามเรียก fully tested จาก unit suite อย่างเดียว

## 7. เพิ่ม format หรือ feature

### Output format

ตรวจ extension, container, codec, encoder availability, stream maps, quality semantics และ metadata เพิ่ม command/naming/invalid-value/integration tests

### Trim

Normalize time, reject reversed/out-of-range, นิยาม seeking accuracy, ใช้ effective duration กับ progress และ test A/V sync

### Batch

สร้าง job queue/controller แยกจาก widget นิยาม collision, failure continuation, cancellation และ aggregate progress ก่อนทำ UI เริ่ม sequential

### Platform preset

เก็บ constraints เป็น data แยกจาก import URL ระบุ fit/crop/pad, dimension, codec, frame rate และ audio โดยไม่อ้าง official endorsement

### URL/account import

URL import ปัจจุบันรองรับ public single-item ผ่าน yt-dlp โดยไม่มี account/cookies และแยกจาก converter การเพิ่ม provider/account scope ต้องอ่าน official API/terms ปัจจุบัน นิยาม authorization, credential storage, retention และ policy ใหม่ ห้าม DRM/access-control bypass

## 8. Documentation และ release readiness

เมื่อ behavior เปลี่ยน ให้อัปเดต README, USER_GUIDE และ TROUBLESHOOTING ที่เกี่ยวข้อง

ก่อน release ต้องมี:

- รักษา GPLv3 license และ copyright/license notices
- Test suite ผ่าน
- Manual GUI smoke test
- Clean-machine test
- FFmpeg distribution/licensing decision หาก bundle
- Version, release notes และ checksum
- ไม่มี media, log, credential หรือ local path ใน Git

Windows release ใช้ PyInstaller แบบ onedir และ Inno Setup แบบ per-user ห้าม commit `.exe`, `build/` หรือ `dist/` ลง Git

สร้าง release ในเครื่อง:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
.\scripts\build_windows.ps1
```

ข้อกำหนด build: Python 3.10+, Inno Setup 6 และ Windows x64 สคริปต์สร้าง icon, `dist\Clipora`, Setup installer และ `.sha256` ห้าม release หาก test, EXE smoke test หรือ install/open/uninstall cycle ไม่ผ่าน

GitHub workflow `.github/workflows/release.yml` ทำงานเมื่อ push tag `v*` และแนบ Setup/checksum ไปที่ Release การเปลี่ยน dependency manifest ต้องอัปเดต immutable URL, version, SHA-256, source และ license ใน `clipora/dependencies.py` กับ `THIRD_PARTY_NOTICES.md` พร้อมกัน
