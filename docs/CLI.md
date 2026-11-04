# Clipora CLI — ใช้จาก command line

Clipora CLI คือโหมดใช้งานแบบไม่มีหน้าจอ (headless) ของ Clipora สำหรับงานอัตโนมัติและงานเป็นชุด (batch) โดยเรียก core ตัวเดียวกับโปรแกรมเดสก์ท็อป — แปลงไฟล์ในเครื่องด้วย FFmpeg และดาวน์โหลดลิงก์สาธารณะด้วย yt-dlp ไม่มี dependency เพิ่ม ทำงานในเครื่องทั้งหมด

## สิ่งที่ต้องมี

- Python 3.10 ขึ้นไป (รันจากโฟลเดอร์โปรเจกต์)
- งาน `convert` ต้องมี `ffmpeg` และ `ffprobe` ในเครื่อง (ตัวเดียวกับที่โปรแกรมใช้)
- งาน `download` ต้องมี `yt-dlp` (แบบ executable หรือติดตั้งเป็นแพ็กเกจ `yt_dlp`) และ FFmpeg สำหรับรวมไฟล์เสียง/วิดีโอ
- ตรวจเครื่องมือได้ด้วย `python scripts/check_environment.py`

เปิดดูตัวเลือกทั้งหมด:

```powershell
python -m clipora.cli --help
python -m clipora.cli convert --help
python -m clipora.cli download --help
```

## ตัวอย่างการใช้งาน

### แปลงไฟล์เดียว (เสียง MP3)

```powershell
python -m clipora.cli convert "C:\media\clip.mp4"
```

ผลลัพธ์เริ่มต้นอยู่ข้างไฟล์ต้นฉบับ: `C:\media\clip_audio.mp3`

### แปลงหลายไฟล์เป็นชุด

```powershell
python -m clipora.cli convert "C:\media\a.mp4" "C:\media\b.mov" --output-dir "C:\media\out"
```

### แปลงวิดีโอ MP4 คุณภาพสูง 60fps

```powershell
python -m clipora.cli convert "C:\media\clip.mov" --mode video --format mp4 --quality high --fps 60
```

ถ้าไม่ระบุ `--format` โหมด `video` จะได้ MP4 และโหมด `audio` จะได้ MP3 ส่วน `--format` เดี่ยวๆ จะ Infer โหมดให้เอง (mp4/mov = video, mp3/m4a/wav/flac/opus = audio) — ถ้า `--mode` กับ `--format` ขัดกันจะจบด้วย exit code 2

ถ้าไม่ระบุทั้ง `--mode` และ `--format` ค่าเริ่มต้นคือโหมดเสียง MP3 (`audio` + `mp3`)

### ตัดช่วงเวลา

```powershell
python -m clipora.cli convert "C:\media\podcast.mp3" --format m4a --trim-start 00:01:30 --trim-duration 30
```

`--trim-start` และ `--trim-duration` รับได้ทั้งวินาที (`90`, `90.5`) และ `MM:SS`/`HH:MM:SS` เว้นว่างคือไม่ตัด (ตัดจากต้นหรือถึงท้ายไฟล์ตามช่องที่กรอก)

### ปรับเสียงพอดแคสต์

```powershell
python -m clipora.cli convert "C:\media\voice.m4a" --format mp3 --enhance
```

### ดาวน์โหลดลิงก์สาธารณะ

```powershell
python -m clipora.cli download "https://example.com/watch?v=abc" --format mp3 --output-dir "C:\media\downloads"
python -m clipora.cli download "https://example.com/watch?v=abc" --mode video --quality high
```

ค่าเริ่มต้นของงานดาวน์โหลดคือบันทึกในโฟลเดอร์ปัจจุบัน (`--output-dir` เพื่อเปลี่ยน) และคุณภาพแบบวิดีโอแมปเป็นความละเอียด: `high` = สูงสุด, `balanced` = 1080p, `small` = 720p

### ผลลัพธ์แบบ JSON (สำหรับ automation)

```powershell
python -m clipora.cli convert "C:\media\a.mp4" "C:\media\b.mp4" --json
```

- `--json` พิมพ์สรุปผลเป็น JSON บรรทัดเดียวที่ **stdout** และปิด progress ทั้งหมด
- progress ปกติ (แบบไม่ใช้ `--json`) พิมพ์ที่ **stderr** ส่วนสรุปผลพิมพ์ที่ stdout จึงแยก parse ได้
- ข้อความ diagnostic ของไฟล์ที่ล้มเหลว (ข้อความ error) ยังพิมพ์ที่ **stderr** แม้ใช้ `--json` — stdout จะมีเฉพาะ JSON ก้อนเดียว
- จะ **ไม่มี JSON** เลยเมื่อจบด้วย exit code `2` (usage error) หรือเมื่อกด `Ctrl+C` ครั้งที่สอง (ออกทันที) เพราะยังไม่ถึงขั้นสรุปผล

ตัวอย่าง JSON:

```json
{"command": "convert", "exit_code": 0, "cancelled": false, "total": 1, "succeeded": 1, "failed": 0, "skipped": 0, "items": [{"index": 1, "input": "C:\\media\\a.mp4", "output": "C:\\media\\a_audio.mp3", "status": "ok", "error": null}]}
```

สถานะของแต่ละรายการ (`status`) คือ `ok`, `failed`, `skipped` หรือ `cancelled` — ตัวเลข `skipped` นับรวมรายการที่ถูกยกเลิกด้วย

### ชื่อไฟล์ชนกัน และ `--overwrite`

- ค่าเริ่มต้น: Clipora ไม่เขียนทับไฟล์เดิม จะเติมเลขให้เป็น `ชื่อ (1).mp3`, `ชื่อ (2).mp3` … (ใช้กับทั้ง `convert` และ `download`)
- `--overwrite`: เขียนทับไฟล์เดิมชื่อเดียวกันได้ (งาน `convert` ส่ง overwrite ให้ core; งาน `download` ส่ง conflict callback ให้ core)
- ภายใน batch เดียวกัน ชื่อผลลัพธ์จะไม่ชนกัน **แม้ใช้ `--overwrite`** — ไฟล์เดิมที่มีอยู่แล้วจะถูกเขียนทับได้เฉพาะ "ครั้งแรก" ที่ batch ใช้ชื่อนั้น ส่วนรายการถัดไปที่ได้ชื่อซ้ำจะถูกเติมเป็น `(1)`, `(2)` แทน (งาน `download` ใช้ callback ตอบ "เก็บทั้งสอง" ให้ core เติมเลขเอง โดยอิงชื่อไฟล์ที่ core คืนมาจริง)
- การจองชื่อคิดแยก **ตามโฟลเดอร์ปลายทาง**: ถ้าไม่ใส่ `--output-dir` ไฟล์ `a\clip.mp4` และ `b\clip.mp4` จะได้ `a\clip_audio.mp3` และ `b\clip_audio.mp3` ตามโฟลเดอร์ของตัวเอง (ไม่ถูกเติม `(1)` ข้ามโฟลเดอร์)

### ทำต่อเมื่อไฟล์หนึ่งล้มเหลว

```powershell
python -m clipora.cli convert "C:\media\a.mp4" "C:\media\b.mp4" "C:\media\c.mp4" --continue-on-error
```

ค่าเริ่มต้นคือหยุดเมื่อพบข้อผิดพลาดแรกและทำเครื่องหมายไฟล์ที่เหลือเป็น `skipped`; ใส่ `--continue-on-error` เพื่อทำงานจนจบทุกไฟล์แล้วสรุปผลรวม

### ยกเลิกด้วย Ctrl+C

- กด `Ctrl+C` ครั้งแรก: ยกเลิกงานปัจจุบันแบบสะอาด — ส่ง `CancellationToken.cancel()` ให้ core เพื่อฆ่า process ที่กำลังทำงาน (ไม่ฆ่าตามชื่อ process) ล้างไฟล์ชั่วคราว และรักษาไฟล์ผลลัพธ์เดิมไว้
- กด `Ctrl+C` ครั้งที่สอง: ออกทันที
- ไม่มี traceback หลุดออกมา และจบด้วย exit code `130` — รวมถึงกรณีกด `Ctrl+C` ระหว่างการตรวจอาร์กิวเมนต์ (ก่อนเริ่มงาน) ด้วย

## Exit codes

| Code | ความหมาย |
|---|---|
| `0` | สำเร็จทุกไฟล์ |
| `1` | มีไฟล์ที่ล้มเหลว หรือ batch ถูกหยุดกลางทาง (ยังไม่ถูก Ctrl+C) |
| `2` | อาร์กิวเมนต์ไม่ถูกต้อง (เช่น `--mode` ขัดกับ `--format`, trim รูปแบบผิด, ลิงก์ไม่ผ่านการตรวจ, ไม่ได้ระบุไฟล์/URL) |
| `130` | ถูกยกเลิกด้วย `Ctrl+C` |

## ตัวเลือกทั้งหมด

| ตัวเลือก | ค่า | ค่าเริ่มต้น | ใช้กับ |
|---|---|---|---|
| `--mode` | `audio`, `video` | อนุมานจาก `--format` | ทั้งสอง |
| `--format` | `mp3`, `m4a`, `wav`, `flac`, `opus`, `mp4`, `mov` | `mp3` (audio) / `mp4` (video) | ทั้งสอง |
| `--quality` | `high`, `balanced`, `small` | `balanced` | วิดีโอ (convert) / download (แมปเป็นความละเอียด) |
| `--fps` | `max`, `60`, `30` | `max` | วิดีโอ |
| `--trim-start` | วินาที / `MM:SS` / `HH:MM:SS` | ไม่ตัด | ทั้งสอง |
| `--trim-duration` | วินาที / `MM:SS` / `HH:MM:SS` | ถึงท้ายไฟล์ | ทั้งสอง |
| `--enhance` | flag | ปิด | ทั้งสอง |
| `--output-dir` | โฟลเดอร์ | โฟลเดอร์ต้นฉบับ (convert) / โฟลเดอร์ปัจจุบัน (download) | ทั้งสอง |
| `--overwrite` | flag | ปิด (เติมเลข `(1)`) | ทั้งสอง |
| `--continue-on-error` | flag | ปิด (หยุดที่ error แรก) | ทั้งสอง |
| `--json` | flag | ปิด | ทั้งสอง |

หมายเหตุ: `--quality` มีผลกับงานแปลง **วิดีโอ** (ระดับคุณภาพการเข้ารหัส) และงาน `download` (แมปเป็นความละเอียด `สูงสุด`/`1080p`/`720p`) เท่านั้น — งาน `convert` โหมดเสียง (MP3/M4A/WAV/FLAC/OPUS) ไม่ได้ใช้ค่านี้

## ข้อจำกัด

- งาน `download` รองรับเฉพาะลิงก์ **สาธารณะทีละรายการ** เท่านั้น — ไม่รองรับ playlist, live stream, private/paid media, การเข้าสู่ระบบ, cookies หรือการบายพาส DRM ผู้ใช้ต้องเป็นเจ้าของสื่อ ได้รับอนุญาต หรือมีสิทธิ์ตามกฎหมายและเงื่อนไขของแหล่งนั้น
- งาน `download` ต้องมี `yt-dlp`; เว็บไซต์อาจเปลี่ยนระบบจนต้องอัปเดต yt-dlp ก่อนใช้ได้
- ไม่มีโหมดแยก Stem (Demucs) ใน CLI — ฟีเจอร์นี้ยังใช้ได้เฉพาะในโปรแกรมเดสก์ท็อป
- `--format mov` (ProRes) ต้องมี FFmpeg ที่รองรับ encoder ProRes มิฉะนั้นจะรายงานเป็นไฟล์ล้มเหลว
- การตัดช่วงในงาน `download` อ้างอิง keyframe ของวิดีโอ จุดตัดอาจคลาดเคลื่อนเล็กน้อย
- งาน `convert` ตรวจ stream ของผลลัพธ์ก่อนประกาศสำเร็จ (เหมือนโปรแกรมหลัก) จึงต้องมี `ffprobe`
- CLI ทำงานแบบเรียงทีละไฟล์ ไม่มี parallel batch
- เอกสารนี้อ้างอิงพฤติกรรมของ core ปัจจุบัน; ถ้าแก้ `clipora/conversion.py`, `clipora/importer.py` หรือ `clipora/ffmpeg.py` ต้องอัปเดต CLI และเอกสารนี้ด้วย
