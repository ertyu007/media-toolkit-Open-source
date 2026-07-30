# Contributing to Clipora

ขอบคุณที่สนใจร่วมพัฒนา Clipora โปรดรักษาเป้าหมาย local-first, source-safe และใช้งานง่ายบน Windows

## ก่อนเริ่ม

1. อ่าน [README.md](README.md) และ [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)
2. ค้นหา issue เดิมก่อนเปิดใหม่
3. สำหรับ feature ใหญ่ ให้เปิด discussion/issue เพื่อกำหนด scope ก่อนเขียน
4. อย่าแนบ media ส่วนตัว credential cookie token หรือพาธที่เปิดเผยข้อมูลส่วนตัว

## ตั้งค่า

```powershell
git clone https://github.com/ertyu007/media-toolkit-Open-source.git
cd media-toolkit-Open-source
python scripts/check_environment.py
python -m unittest discover -s tests -v
```

สร้าง branch ที่สื่อความหมาย:

```powershell
git switch -c fix/progress-parser
```

## รูปแบบการเปลี่ยนแปลง

- หนึ่ง pull request ต่อหนึ่ง outcome หลัก
- แบ่ง feature ใหญ่เป็น vertical slices ที่รันได้
- อย่าปน refactor ที่ไม่เกี่ยวข้อง
- รักษา Python 3.10+ compatibility
- ใช้ type hints ใน core/public functions
- ใช้ `pathlib.Path` สำหรับ local paths
- ใช้ subprocess argument list ห้าม `shell=True`
- ห้ามแตะ Tkinter จาก worker thread
- ห้ามแก้หรือลบ source media
- เพิ่ม dependency เมื่อจำเป็นจริง พร้อมเหตุผล version constraint docs และ packaging impact

## Tests ที่ต้องรัน

```powershell
python -m compileall -q app.py clipora tests scripts
python -W error::ResourceWarning -m unittest discover -s tests -v
```

เพิ่ม regression test สำหรับ bug และ integration test เมื่อเปลี่ยน FFmpeg command, stream, codec, progress หรือ finalization

หากไม่ได้รัน manual GUI หรือ integration test ให้ระบุใน PR ชัดเจน

## Commit และ Pull Request

ใช้ commit message ที่อธิบายผล เช่น:

```text
fix: reject audio extraction from silent video
test: cover Unicode output paths
docs: explain FFmpeg PATH setup
```

PR description ควรมี:

```text
Outcome:
Why:
Files/architecture affected:
Tests run and result:
Manual checks:
Not tested:
Screenshots for UI changes:
Privacy/security/license impact:
```

## Media fixtures

- สร้าง fixture ขนาดเล็กด้วย FFmpeg lavfi เมื่อเป็นไปได้
- ใช้ temporary directory
- อย่า commit ไฟล์ media ขนาดใหญ่
- ต้องมีสิทธิ์เผยแพร่ fixture ทุกไฟล์
- ตัด metadata ส่วนตัวก่อนแนบ

## Bug report

แนบ exact error, ขั้นตอนทำซ้ำ, Python/FFmpeg versions, operation/settings, sanitized stream summary และ test results อ่าน [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) ก่อน

## Feature requests

อธิบาย user problem, observable outcome, use case ของ owned/authorized media, non-goals, UI impact, local/network boundary และ acceptance criteria

คำขอที่เกี่ยวกับ downloader, account, cookies, DRM หรือ platform restrictions ต้องมี official API/terms path และ security/privacy review ก่อน implementation

## Review checklist

- Source ไม่เปลี่ยน
- Overwrite/collision ชัดเจน
- UI ไม่ block และ thread boundary ถูกต้อง
- Error กลับสู่ usable state
- Logs bounded และไม่มี secret
- Tests/docs ตรง behavior
- ไม่มี generated artifact หรือ media หลุดเข้า Git
