# Clipora

Clipora คือโปรแกรมเดสก์ท็อปโอเพนซอร์สสำหรับ Windows สำหรับดาวน์โหลดสื่อสาธารณะที่ได้รับอนุญาต แยกเสียง และแปลงวิดีโอ โดยไม่มีโฆษณา ไม่มีบัญชี Clipora และไม่มีค่าประมวลผลบนเซิร์ฟเวอร์ ไฟล์ในเครื่องจะไม่ถูกอัปโหลด ส่วนโหมดลิงก์เชื่อมต่อเว็บไซต์ต้นทางผ่าน `yt-dlp` แล้วประมวลผลผลลัพธ์บนเครื่อง

> รุ่น 0.4 เพิ่ม Windows installer และ Setup Assistant ผู้ใช้ทั่วไปไม่ต้องติดตั้ง Python หรือแก้ PATH เอง

## ติดตั้งสำหรับผู้ใช้ทั่วไป

1. เปิดหน้า [GitHub Releases](https://github.com/ertyu007/media-toolkit-Open-source/releases)
2. ดาวน์โหลด `Clipora-Setup-<version>-x64.exe` และไฟล์ `.sha256` ที่อยู่คู่กัน
3. เปิดตัวติดตั้ง เลือกสร้างไอคอนบน Desktop ได้ตามต้องการ ไม่ต้องใช้สิทธิ์ Administrator
4. เปิด Clipora ครั้งแรก ตัวช่วยตั้งค่าจะแสดงก่อนหน้าหลัก
5. กด **ถัดไป** อ่านและยอมรับข้อตกลง จากนั้นตรวจรายการ FFmpeg, yt-dlp และ Deno รวมถึงขนาดดาวน์โหลด
6. กด **ติดตั้ง** แล้วรอการดาวน์โหลดจาก release ทางการ การตรวจ SHA-256 และการติดตั้งลง `%LOCALAPPDATA%\Clipora\tools`
7. เมื่อขึ้น **Clipora พร้อมใช้งานแล้ว** กด **เสร็จสิ้น** เพื่อเปิดหน้าหลัก

ไฟล์ Setup รวม Python/Tkinter ไว้แล้ว การดาวน์โหลดเครื่องมือเกิดขึ้นครั้งแรกหรือเมื่อผู้ใช้เลือก **เครื่องมือ → ติดตั้งใหม่ / ซ่อมเครื่องมือ** เท่านั้น ขนาดดาวน์โหลดครั้งแรกประมาณ 170 MB

## ความสามารถปัจจุบัน

- วางลิงก์สาธารณะจาก YouTube, Facebook, Instagram และเว็บไซต์ที่ yt-dlp รองรับ
- ดาวน์โหลดวิดีโอแบบคุณภาพสูงสุด, 1080p, 720p หรือ 480p
- ดาวน์โหลดเฉพาะเสียงเป็น MP3 หรือ M4A
- แยกเสียงจากวิดีโอเป็น MP3 หรือ M4A
- แปลงวิดีโอเป็น MP4 แบบ H.264/AAC
- เลือกคุณภาพ High, Balanced หรือ Small
- แสดงชื่อ/ขนาดไฟล์ ความคืบหน้า และตรวจ stream ก่อนเริ่ม
- ล็อกตัวเลือกระหว่างประมวลผลเพื่อป้องกันสถานะหน้าจอสับสน
- ยกเลิกงานที่กำลังทำและล้างเฉพาะไฟล์ชั่วคราวของงาน
- รักษา output เดิมไว้จนกว่างานใหม่จะสำเร็จสมบูรณ์
- รองรับพาธภาษาไทย ช่องว่าง และอักขระพิเศษ
- ประมวลผลในเครื่องและไม่แก้ไขไฟล์ต้นฉบับ

โหมดลิงก์รองรับทีละรายการและไม่รับ playlist, live stream, private/paid media, login, cookies หรือ DRM เว็บไซต์อาจเปลี่ยนระบบจนต้องอัปเดต yt-dlp ผู้ใช้ต้องเป็นเจ้าของสื่อ ได้รับอนุญาต หรือมีสิทธิ์ตามกฎหมายและเงื่อนไขของแหล่งนั้น

## สิ่งที่ต้องมีสำหรับรุ่น Setup

| รายการ | รายละเอียด |
|---|---|
| ระบบ | Windows 10 หรือ 11 |
| สถาปัตยกรรม | Windows x64 |
| อินเทอร์เน็ตครั้งแรก | สำหรับดาวน์โหลดเครื่องมือประมาณ 170 MB |
| พื้นที่ว่าง | มากพอสำหรับไฟล์ผลลัพธ์ |

Setup Assistant ใช้ flow แบบ Welcome → ข้อตกลง → ตรวจรายการ → ติดตั้ง → เสร็จสิ้น และไม่ดาวน์โหลดไฟล์แบบเงียบ ผู้ใช้ต้องยินยอมและกดติดตั้งก่อน ทุก URL ใช้ HTTPS มีขีดจำกัดขนาด และตรวจ checksum ที่ pin ไว้ก่อนติดตั้ง ครั้งถัดไปจะข้ามตัวช่วยเมื่อเครื่องมือครบแล้ว

## Clone และเปิดใช้งานสำหรับนักพัฒนา

```powershell
git clone https://github.com/ertyu007/media-toolkit-Open-source.git
cd media-toolkit-Open-source
python --version
```

ติดตั้ง FFmpeg และ yt-dlp บน Windows:

```powershell
winget install Gyan.FFmpeg
winget install yt-dlp.yt-dlp
winget install DenoLand.Deno
```

เปิด PowerShell ใหม่ แล้วตรวจ environment:

```powershell
python scripts/check_environment.py
```

เมื่อทุกหัวข้อขึ้น `[OK]` ให้เปิดโปรแกรม:

```powershell
python app.py
```

ไม่ต้องเปิด PowerShell ด้วยสิทธิ์ Administrator

สร้าง Windows installer สำหรับทดสอบ release:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
.\scripts\build_windows.ps1
```

ต้องใช้ Python 3.10+ และ Inno Setup 6 ผลลัพธ์อยู่ที่ `dist\installer` การ push tag เช่น `v0.4.1` จะให้ GitHub Actions ทดสอบ สร้าง Setup และแนบ checksum ไปยัง GitHub Release อัตโนมัติ

## วิธีใช้แบบย่อ

1. เลือก **ไฟล์ในเครื่อง** หรือ **วางลิงก์**
2. เลือกโฟลเดอร์บันทึก
3. เลือกเสียง MP3/M4A หรือวิดีโอและระดับคุณภาพ
4. สำหรับลิงก์ ให้ยืนยันว่ามีสิทธิ์ดาวน์โหลดสื่อนั้น
5. กดปุ่มเริ่ม รอผลสำเร็จ หรือกดยกเลิกได้
6. เปิดโฟลเดอร์ผลลัพธ์จากโปรแกรมได้ทันที

งานไฟล์ในเครื่องจะถามก่อนเขียนทับ ส่วนงานลิงก์จะสร้างชื่อ `(1)`, `(2)` เพื่อรักษาไฟล์เดิม และไม่แก้ไขต้นฉบับ อ่านทุกตัวเลือกใน [คู่มือผู้ใช้](docs/USER_GUIDE.md)

## เอกสาร

- [คู่มือผู้ใช้](docs/USER_GUIDE.md)
- [แก้ปัญหาและเก็บ Error Log](docs/TROUBLESHOOTING.md)
- [คู่มือพัฒนาและ Architecture](docs/DEVELOPMENT.md)
- [แนวทางร่วมพัฒนา](CONTRIBUTING.md)
- [รายงานช่องโหว่](SECURITY.md)

## ทดสอบ

```powershell
python -m compileall -q app.py clipora tests scripts
python -W error::ResourceWarning -m unittest discover -s tests -v
```

Integration tests สร้างสื่อขนาดเล็กใน temporary directory และ skip เมื่อไม่พบ FFmpeg

## Roadmap ระยะใกล้

- ตัดช่วงเวลาและ batch processing
- Code signing เพื่อลดคำเตือน SmartScreen
- Portable ZIP และ Full Offline installer
- เพิ่ม export presets

## License

Clipora เผยแพร่ภายใต้ [GNU General Public License v3.0](LICENSE) (`GPL-3.0-only`) ผู้ที่แจกจ่ายโปรแกรมหรือเวอร์ชันดัดแปลงต้องปฏิบัติตามเงื่อนไขของ GPLv3 และจัดเตรียม source code ที่สอดคล้องกัน

Windows Setup รวม Python runtime แต่ไม่รวม FFmpeg, yt-dlp หรือ Deno ตัว Setup Assistant ดาวน์โหลดจากผู้เผยแพร่โดยตรง ดูเวอร์ชัน แหล่งที่มา checksum และ license ใน [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
