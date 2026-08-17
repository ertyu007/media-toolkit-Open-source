# บันทึกงาน (Work Notes) — ฟีเจอร์แยกสเต็มเสียง (Stem Separation) + อัปเดต yt-dlp

อัปเดตล่าสุด: 2026-08-17

## สถานะโดยรวม

- ฟีเจอร์ **แยกสเต็มเสียง (stems)** ผ่านการ implement ครบและทดสอบผ่านแล้ว
- ฟีเจอร์ **อัปเดต yt-dlp** (ปุ่มในแอป + ตรวจอัตโนมัติตอนเปิดแอป) implement ครบและทดสอบผ่านแล้ว
- ชุดเทสต์เต็ม: **138 tests ผ่าน** (skipped 2 = network) — รันบน Python 3.13 (venv สร้างใหม่)
- ทดสอบจริง end-to-end ฟีเจอร์ stems แล้ว (Demucs บน CPU, เอาต์พุต `_vocals.mp3` + `_instrumental.mp3` + `_stems.zip`)
- **ติดตั้งเครื่องมือ separator จริงแล้ว** — `%LOCALAPPDATA%\Clipora\tools\separator` (~209 MB), `test_separator_integration.py` รันผ่าน 2/2
- **ทดสอบจริง flow อัปเดต yt-dlp แล้ว** — วาง exe รุ่น 2026.06.09 ลง managed tools แล้ว `update_ytdlp()` อัปเดตเป็น 2026.07.04 ผ่าน (download → checksum → atomic replace → record)
- **อัปเดต docs แล้ว** — `THIRD_PARTY_NOTICES.md` (เพิ่ม separator toolchain + wheel table), `README.md`, `docs/USER_GUIDE.md`

## ทำวันนี้ (2026-08-17)

- แก้ venv เสีย (ชี้ไป Python 3.9 ของ user อื่น) → สร้างใหม่ด้วย Python 3.13 + `requirements-dev.txt`
- แก้ bug ใน `tests/test_separator_integration.py`: `setUpClass` ใช้ `with tempfile.TemporaryDirectory()` ซึ่งลบไฟล์ source ก่อน test รัน → เปลี่ยนเป็นเก็บ tempdir ใน class และ `tearDownClass` cleanup
- **แยกเวอร์ชัน PC/Mobile**: PC กลับเป็น `0.5.1` (mobile คง `1.0.1`) — แก้ `__init__.py`, UA, iss, version_info, README
- **แก้ CI ล้ม**: `test_donate.py` เช็ค `assets/` (gitignored ไม่มีใน CI) → ลบ assert นั้น
- **Donate QR ใช้ไฟล์ที่ commit ตรง ๆ แล้ว**: เดิมเก็บ QR เป็น secret `CLIPORA_DONATE_QR_BASE64` และ decode ใน CI — เปลี่ยนมา commit `assets/donate-qr.png` ไว้ใน repo (เลิก gitignore, ลบ step decode จาก workflow, ลบ `scripts/print_donate_secret.ps1`) เพื่อให้ทุก build มี QR แน่นอน
- **แยกสเต็ม → อัด zip**: `separate_audio()` สร้าง `{ชื่อ}_stems.zip` รวมทุกสเต็ม หลังแยกเสร็จ (ไฟล์แยกยังอยู่) — `create_stems_zip()`, `separate_output_zip_path()`, UI เช็ค overwrite zip ด้วย, test 3 ตัวใหม่ + integration อัปเดต (138 tests ผ่าน)
- **แก้ QR โดเนทไม่ขึ้น + ขึ้นเวอร์ชัน 0.5.2**: `DonateDialog` ใช้ `ttk.Label` style `Card.TFrame` (Frame layout ไม่มี label element) ทำให้ label รูป QR หดเหลือ 1x1 → เปลี่ยนเป็น `Card.TLabel`; เปลี่ยน QR จาก CI secret มาเป็นรูป commit ตรง ๆ; bump ทุกที่ (`__init__`, iss, manifest, version_info, UA ×2, README)

## ฟีเจอร์โดเนท PromptPay (เพิ่ม 2026-08-17)

- ปุ่ม **โดเนท** ที่ header (คอลัมน์ 5) → เปิด `DonateDialog` แสดง QR PromptPay + ข้อความ
- `clipora/donate.py` (ใหม่): `donate_image_path()` ค้นหา `donate-qr.png` จาก `_MEIPASS` / หลัง exe / `assets/` (source)
- QR asset: วางต้นฉบับที่ `assets/pay/promptpayQr.jpg` แล้วแปลงเป็น `assets/donate-qr.png` (Tk อ่าน PNG/GIF ได้ ไม่รองรับ JPG, runtime stdlib-only) ขนาด 320x428
- `packaging/clipora.spec`: เพิ่ม `assets/donate-qr.png` เข้า `datas` (ถ้ามีไฟล์)
- `tests/test_donate.py` (ใหม่): 3 tests ค้นหา asset / ไม่เจอคืน None / bundled มี priority

## ฟีเจอร์อัปเดต yt-dlp (เพิ่ม 2026-08-16)

### การตัดสินใจ/เหตุผล
- ผู้ใช้เลือก: **ปุ่มอัปเดต yt-dlp ในแอป + ตรวจอัตโนมัติตอนเปิดแอป**
- yt-dlp ถูก pin ไว้ที่ `2026.07.04` ใน `dependencies.py` (ยังเป็นเวอร์ชันล่าสุด ณ วันที่ตรวจ — GitHub API)
- ไม่มีกลไก auto-update มาก่อน และ `dependencies_to_install()` จะข้ามถ้ามีอยู่แล้ว
- การอัปเดตเป็นกรณีพิเศษที่ยอมให้ใช้ "ล่าสุด" (ต่างจากกติกา pin ทุกอย่าง) — ยืนยัน checksum จาก `SHA2-256SUMS` ของ GitHub เสมอ

### ไฟล์ที่แก้/เพิ่ม
| ไฟล์ | งาน |
|---|---|
| `clipora/ytdlp_update.py` (ใหม่) | `latest_ytdlp_version()` (GitHub API `releases/latest`), `installed_ytdlp_version()` (อ่านจาก exe + `installed.json`), `is_newer_available()`, `parse_ytdlp_version()`, `update_ytdlp()` — ดาวน์โหลด `yt-dlp.exe` + `SHA2-256SUMS`, ตรวจ sha256, `os.replace` แบบ atomic ลง `managed_tools_dir()/yt-dlp.exe`, เขียน `installed.json` ใหม่ผ่าน `_write_install_record`; HTTPS เท่านั้น, รองรับ progress callback + cancel check |
| `clipora/ui.py` | ปุ่ม "อัปเดต yt-dlp" ที่ header (คอลัมน์ 4), ตรวจอัตโนมัติหลังเปิดแอป 3 วินาที (`self.after(3000, self._maybe_check_ytdlp_update)`), worker ผ่าน thread + `self.after(0, ...)`, guard: ไม่ทำงานตอนมีงานกำลังรัน/เปิด setup dialog, โหมด auto เงียบเมื่อ error/ยังไม่ติดตั้ง, โหมด manual แสดง messagebox; ทำงานผ่าน job infra (`_begin_job/_set_progress/_finish_job/_cancelled`) |
| `tests/test_ytdlp_update.py` (ใหม่) | 16 tests: version parse/compare, GitHub checksum parse, checksum verify, `os.replace` atomic, installed record, HTTPS-only, cancel, update รุ่นที่ไม่ใหม่กว่าข้าม |

### UI flow (ทำงานอย่างไร)
1. เปิดแอป → 3 วิ → `_maybe_check_ytdlp_update()` → thread เช็ค → ถ้ามีรุ่นใหม่ (และไม่ใช่ auto-silent) ถาม `askyesno` → `_start_ytdlp_update`
2. อัปเดต: ดาวน์โหลด + ตรวจ checksum + `os.replace` → แสดง `messagebox.showinfo` เมื่อเสร็จ
3. ถ้ายังไม่ได้ติดตั้ง yt-dlp เลย → แนะนำกดปุ่ม "เครื่องมือ" เพื่อติดตั้งก่อน

### เหตุผลที่ต้องระวัง (pitfall ที่เจอ)
- `zipfile.ZipFile.writestr()` กับ **arcname แบบ string** จะใส่ `time.localtime()` ลง timestamp ใน zip
  → payload ที่สร้างใน test helper (`wheel_zip`/`embed_zip` ใน `tests/test_dependencies.py`)
  **ไม่ deterministic ข้ามการเรียก** → checksum ตรงกันในรอบเดียวแต่ไม่ตรงในอีกรอบ (flaky!
  สลับไปมา เช่น colorama/packaging/anyio/lameenc) แก้โดยส่ง `zipfile.ZipInfo(name, (1980,1,1,0,0,0))`
  (ดูเพิ่มในหัวข้อ "สิ่งที่แก้ bug ระหว่างทาง")

## ไฟล์ที่แก้/เพิ่ม

| ไฟล์ | งาน |
|---|---|
| `clipora/separator.py` (ใหม่) | pipeline หลัก: `demucs -n htdemucs_6s --repo <dir>` offline, parse progress, workspace (`.clipora-separate-*`) + cleanup, amix ประกอบ instrumental, แปลง/บันทึกแต่ละสเต็ม, collision/overwrite |
| `clipora/dependencies.py` | `SEPARATOR_DEPENDENCIES` (32 specs แบบ pin: python-embed 3.13.14, torch 2.13.0+cpu, numpy 2.5.2, demucs 4.1.0 + deps, model `5c90dfd2-34c22ccb.th`), staging แบบ `python-embed`/`python-wheel` (แก้ `._pth` ให้เปิด site-packages), `install_separator_toolchain()`, `install_toolchains()` |
| `clipora/ui.py` | โหมด `stems` ใหม่ (radio), ติ๊กเลือกสเต็ม (`stem_vars`), `_start_stems_local/_url`, `_run_stems_*`, `_done_stems`, progress/phase ของสเต็ม, เรียก `_open_tool_setup(separator=True)` เมื่อยังไม่ติดตั้ง |
| `clipora/setup_ui.py` | พารามิเตอร์ `separator` ใน `ToolSetupDialog`, ใช้ `install_toolchains()`, ข้อความ welcome/summary เพิ่มตอนติดตั้ง separator |
| `clipora/importer.py` | `import_audio_for_processing()` (โหลดเสียงลง workspace โดยยังไม่ finalize) + `cleanup_import_workspace` |
| `clipora/tools.py` | `CLIPORA_SEPARATOR_PYTHON` ใน `TOOL_ENVIRONMENT_VARIABLES` + `bundled_tool_directories()` |
| `scripts/check_environment.py` | `check_separator()` (รายงานสถานะ แต่ไม่บังคับ) |
| `tests/test_separator.py` (ใหม่) | unit: command, progress parse, output paths, workspace security |
| `tests/test_separator_integration.py` (ใหม่) | integration: skip ถ้า `separator_installed()` ไม่จริง |
| `tests/test_dependencies.py` | staging embed/wheel, `install_separator_toolchain`, `install_toolchains` |
| `tests/test_check_environment.py` | `check_separator` ด้วย mock |

## สิ่งที่แก้ bug ระหว่างทาง (สำคัญ)

1. **amix filtergraph** — คำสั่ง instrumental เดิม `amix=...` ไม่มี label + `-map 0:a:0` ทำให้ fail ด้วย
   `Cannot find an unused audio input stream...` แก้โดย label input `[0:a][1:a]...[4:a]` และ `-map [aout]`
2. **ลำดับการติดตั้ง staging** — เดิม `_replace_directory` ย้าย `python` ก่อน ทำให้ wheel ที่อยู่
   ใน `staging/python/site-packages` หาย แก้โดยเรียง destination จาก shallow → deep
   และข้าม destination ที่ ancestor ถูกแทนที่แล้ว
3. **flaky checksum ใน test_dependencies** — `writestr('name', data)` ใส่ timestamp เป็นเวลาปัจจุบัน
   ทำให้ `payload_for()` ให้ค่าไม่คงที่ → `matching_specs()` คำนวณ sha ได้ค่าหนึ่ง แต่ `fake_download`
   เขียนอีกค่าหนึ่ง (สลับไปมาระหว่างรอบ). แก้ใน test helper โดยส่ง `zipfile.ZipInfo(name, (1980,1,1,0,0,0))`
   ให้ `writestr` แทนการส่ง string

## วิธีทดสอบ

```powershell
python -m compileall -q app.py clipora tests scripts
python -m unittest discover -s tests -v
```

## งานต่อ (ยังไม่ทำ)

- [ ] **Manual GUI smoke test** — สลับโหมด audio/video/stems, ติ๊กสเต็ม, overwrite prompt,
      ปุ่มติดตั้งเมื่อยังไม่ติดตั้ง separator, ปุ่ม "อัปเดต yt-dlp" (ตอนยังไม่ติดตั้ง/ติดตั้งแล้ว/อัปเดตล่าสุด),
      ข้อความไทย, scale 100/125/150%
- [ ] ทดสอบ URL flow จริง (YouTube) ด้วย `CLIPORA_RUN_NETWORK_TESTS=1`
- [ ] ทดสอบ cancellation ระหว่างแยกสเต็ม (สร้าง test ไว้ยัง? — ยังไม่มี integration สำหรับ cancel)
- [ ] เช็ค `test_version_is_synchronized_with_packaging_metadata` ถ้าจะ bump version + เขียน release notes

## หมายเหตุ/ข้อควรรู้

- โมเดล: `htdemucs_6s` จาก
  `https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/5c90dfd2-34c22ccb.th`
  (sha256 ขึ้นต้น `34c22ccb` ตรงกับชื่อไฟล์) วางที่ `separator/models/htdemucs_6s.th`
- ใช้ `--repo <separator_models_dir>` เพื่อบังคับ offline (ไม่พึ่ง HuggingFace)
- ต้องมี **numpy** ด้วย (demucs/audio.py import numpy ตอน runtime)
- `find_separator_python()` รองรับ `CLIPORA_SEPARATOR_PYTHON` override สำหรับ dev
- `stage_bundled_tools.py` ยังใช้แค่ `WINDOWS_X64_DEPENDENCIES` — separator ไปดาวน์โหลดตอน install ไม่ bundle
- อย่าลืมว่าไฟล์บางไฟล์มี warning CRLF→LF จาก git — ปกติ ไม่กระทบ