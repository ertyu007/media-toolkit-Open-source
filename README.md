<img src="assets/header.svg" alt="ertyu007" width="100%" />

# Clipora

[![Release](https://img.shields.io/github/v/release/ertyu007/media-toolkit-Open-source)](https://github.com/ertyu007/media-toolkit-Open-source/releases) [![Downloads](https://img.shields.io/github/downloads/ertyu007/media-toolkit-Open-source/total)](https://github.com/ertyu007/media-toolkit-Open-source/releases) [![License](https://img.shields.io/github/license/ertyu007/media-toolkit-Open-source)](LICENSE)

Clipora คือโปรแกรมเดสก์ท็อปโอเพนซอร์สสำหรับ Windows แปลงวิดีโอ แยกเสียง และดาวน์โหลดสื่อสาธารณะที่ได้รับอนุญาต — ฟรี ไม่มีโฆษณา ไม่มีบัญชี ประมวลผลบนเครื่องทั้งหมด

พัฒนาโดย `ertyu007` • License [GPL-3.0](LICENSE)

ดาวน์โหลดไฟล์จากหน้า [GitHub Releases](https://github.com/ertyu007/media-toolkit-Open-source/releases) โดยเลือก tag `pc-v*`

---

# Clipora PC (เดสก์ท็อป Windows)

## มีอะไรใหม่ใน 0.6.4

- เมนูตัวเลือก (dropdown) ปิดเองเมื่อลากหน้าต่างหรือเลื่อนจอ ไม่ค้างกลางจออีก และกดปิดหน้าต่างได้เสมอแม้เมนูเปิดอยู่
- คำศัพท์เทคนิคเป็นอังกฤษ: `Stem` (เดิมสะกด `สเต็ม`), `FPS` (เดิม `เฟรมเรต`) ทั้งในโปรแกรมและคู่มือ
- เมนูตัวเลือกและการแจ้งเตือนมีเงา + ขอบ อ่านง่ายขึ้นทั้งธีมมืด/สว่าง
- ปุ่มถอนการติดตั้งย้ายไปฝั่งซ้าย ซ่อนไว้หลังปุ่มพับ กันกดโดน (การยืนยันก่อนถอนยังอยู่ครบ)
- ปุ่มถังขยะในประวัติรวมเข้าแถบตัวกรอง กดแล้วแถบสไลด์ตามปกติ
- มีหน้าเว็บโครงการแล้วที่ https://ertyu007.github.io/media-toolkit-Open-source/

ดูประวัติรุ่นทั้งหมดที่หน้า [Releases](https://github.com/ertyu007/media-toolkit-Open-source/releases)

## ติดตั้งสำหรับผู้ใช้ทั่วไป

1. เปิดหน้า [GitHub Releases](https://github.com/ertyu007/media-toolkit-Open-source/releases) แล้วเลือก tag `pc-v<เวอร์ชัน>` ล่าสุด
2. ดาวน์โหลด `Clipora-Setup-<version>-x64.exe` และไฟล์ `.sha256` ที่อยู่คู่กัน (หรือเลือก `Clipora-<version>-x64.zip` แบบพกพาได้ ไม่ต้องติดตั้ง แค่แกะ zip แล้วรัน `Clipora.exe`)
3. ตรวจ checksum ก่อนติดตั้ง: รัน `Get-FileHash -Algorithm SHA256 <ไฟล์ที่โหลดมา>` แล้วเทียบกับข้อความในไฟล์ `.sha256`
4. รันตัวติดตั้ง เลือกสร้างไอคอนบน Desktop ได้ตามต้องการ (ตัวติดตั้งขอสิทธิ์ Administrator เพราะติดตั้งระดับเครื่อง ส่วนการใช้งานเปิดแบบผู้ใช้ปกติ ไม่ต้อง Run as administrator)
5. เปิด Clipora แล้วใช้งานได้ทันที ไม่ต้องดาวน์โหลดเครื่องมือเพิ่ม

### การแจ้งเตือน Windows SmartScreen หรือ Antivirus (False Positive)

สำหรับเวอร์ชัน Open Source ที่เพิ่งปล่อยใหม่ หาก Windows แสดงหน้าต่างสีฟ้า **"Windows protected your PC" (SmartScreen)**:
- **สาเหตุ:** เป็นพฤติกรรมปกติของ Windows เมื่อพบไฟล์ติดตั้งของโปรแกรมโอเพนซอร์สที่เพิ่งเปิดตัวใหม่และยังไม่ได้ซื้อใบรับรองดิจิทัลแบบชำระเงินรายปี (Code Signing Certificate)
- **วิธีเปิดใช้งาน:** คลิกที่ข้อความ **"More info" (ข้อมูลเพิ่มเติม)** → จากนั้นกดปุ่ม **"Run anyway" (เรียกใช้ต่อไป)**
- **การตรวจสอบความปลอดภัยด้วยตนเอง:** คุณสามารถนำค่า **SHA-256 Hash** หรืออัปโหลดไฟล์ `.exe` ขึ้นตรวจบน [VirusTotal](https://www.virustotal.com/) ได้ด้วยตัวเอง และตรวจสอบโค้ดทั้งหมดได้จาก Repository นี้อย่างโปร่งใส

ไฟล์ Setup รวม Python/Tkinter และ FFmpeg, yt-dlp, Deno ไว้ในตัว (ขนาดตัวติดตั้งประมาณ 250 MB) โดยปิดการบีบอัดแบบ Packer (UPX = False) เพื่อความปลอดภัยสูงสุด ตัวช่วยตั้งค่า (Setup Assistant) จะแสดงเฉพาะเมื่อเครื่องมือบางตัวหายหรือผู้ใช้เลือก **เครื่องมือ → ติดตั้งใหม่ / ซ่อมเครื่องมือ** เท่านั้น

## ความสามารถปัจจุบัน

- วางลิงก์สาธารณะจาก YouTube, Facebook, Instagram และเว็บไซต์ที่ yt-dlp รองรับ
- ดาวน์โหลดวิดีโอแบบคุณภาพสูงสุด, 2160p (4K), 1080p, 720p, 480p หรือ 360p
- ดาวน์โหลดเฉพาะเสียงเป็น MP3, M4A, WAV, FLAC หรือ OPUS
- แยกเสียงจากวิดีโอเป็น MP3, M4A, WAV, FLAC หรือ OPUS
- **แยก Stem เสียง** (เสียงร้อง + ดนตรี และ Stem อื่นๆ) บนเครื่องด้วย Demucs โดยไม่ต้องเชื่อมอินเทอร์เน็ต พร้อมไฟล์ `_stems.zip` รวมทุก Stem
- **อัปเดต yt-dlp** ภายในแอป ตรวจอัตโนมัติตอนเปิด และตรวจ checksum จากผู้เผยแพร่ทุกครั้ง
- แปลงวิดีโอเป็น MP4 แบบ H.264/AAC
- แปลงวิดีโอเป็น MOV แบบ ProRes 422 (รองรับการ import ใน Adobe After Effects)
- ตัดช่วงเวลาสำหรับไฟล์ในเครื่อง (โหมดแยกเสียง/แปลงวิดีโอ): กรอกจุดเริ่ม (วินาทีหรือ HH:MM:SS) และระยะเวลา เว้นว่างไว้คือใช้ทั้งไฟล์
- เลือก FPS สูงสุดของผลลัพธ์ได้ (สูงสุด, 60fps หรือ 30fps)
- เลือกคุณภาพ High, Balanced หรือ Small
- ตรวจพื้นที่ดิสก์ก่อนเริ่มงาน และล้างโฟลเดอร์ชั่วคราวที่ค้างจากงานก่อนให้อัตโนมัติ
- แจ้งเตือนเมื่อมี Clipora เวอร์ชันใหม่ (ตรวจอัตโนมัติตอนเปิด หรือสั่งตรวจเองจากเมนู)
- แสดงชื่อ/ขนาดไฟล์ ความคืบหน้า และตรวจ stream ก่อนเริ่ม
- ล็อกตัวเลือกระหว่างประมวลผลเพื่อป้องกันสถานะหน้าจอสับสน
- ยกเลิกงานที่กำลังทำและล้างเฉพาะไฟล์ชั่วคราวของงาน
- รักษา output เดิมไว้จนกว่างานใหม่จะสำเร็จสมบูรณ์
- รองรับพาธภาษาไทย ช่องว่าง และอักขระพิเศษ
- ประมวลผลในเครื่องและไม่แก้ไขไฟล์ต้นฉบับ

โหมดลิงก์รองรับทีละรายการและไม่รับ playlist, live stream, private/paid media, login, cookies หรือ DRM เว็บไซต์อาจเปลี่ยนระบบจนต้องอัปเดต yt-dlp ผู้ใช้ต้องเป็นเจ้าของสื่อ ได้รับอนุญาต หรือมีสิทธิ์ตามกฎหมายและเงื่อนไขของแหล่งนั้น

## Android (กำลังทำ — โครงพร้อม build แล้ว)

สาขา Android อยู่ใน `android/` แยกจากตัว PC — ประมวลผลบนเครื่อง Android ทั้งหมด ไม่ต้องมีเซิร์ฟเวอร์

- แปลงเป็น MP3, M4A, WAV, FLAC, OPUS และแปลงวิดีโอเป็น MP4 (H.264/AAC)
- ตัดช่วงเวลา, จำกัดเฟรมเรต, เลือกคุณภาพ, แปลงทีละหลายไฟล์, ยกเลิกงานได้
- ดาวน์โหลดลิงก์สาธารณะทีละรายการผ่าน yt-dlp (เสียง/วิดีโอ)
- ไม่มีแยก Stem (Demucs ไม่มี wheel สำหรับ Android) และไม่มี ProRes
- ผลลัพธ์อยู่ใน `Android/data/com.clipora/files/output`

รายละเอียดการ build และข้อจำกัดด้านแพลตฟอร์ม: [`android/README.md`](android/README.md)

## สิ่งที่ต้องมีสำหรับรุ่น Setup

| รายการ | รายละเอียด |
|---|---|
| ระบบ | Windows 10 หรือ 11 |
| สถาปัตยกรรม | Windows x64 |
| อินเทอร์เน็ต | สำหรับดาวน์โหลดตัวติดตั้งประมาณ 250 MB (รวมเครื่องมือแล้ว) |
| พื้นที่ว่าง | มากพอสำหรับตัวติดตั้งและไฟล์ผลลัพธ์ |

ตัวติดตั้งรวม FFmpeg, yt-dlp และ Deno ไว้แล้ว จึงทำงานได้โดยไม่ต้องเชื่อมต่ออินเทอร์เน็ตตอนติดตั้ง สำหรับการติดตั้งใหม่หรือซ่อมเครื่องมือ Setup Assistant ใช้ flow แบบ Welcome → ข้อตกลง → ตรวจรายการ → ติดตั้ง → เสร็จสิ้น และไม่ดาวน์โหลดไฟล์แบบเงียบ ผู้ใช้ต้องยินยอมและกดติดตั้งก่อน ทุก URL ใช้ HTTPS มีขีดจำกัดขนาด และตรวจ checksum ที่ pin ไว้ก่อนติดตั้ง

ตัวติดตั้งรองรับการลงนาม Authenticode แล้ว (แบบ .pfx หรือ Azure Trusted Signing) เพื่อลดคำเตือน SmartScreen และ false positive ของ antivirus ดู [docs/CODE_SIGNING.md](docs/CODE_SIGNING.md) build ที่ยังไม่ลงนามจะได้ตัวติดตั้งแบบเดียวกับเดิม

## Clipora เหมาะกับใคร

Clipora คือเครื่องมือแปลงวิดีโอ YouTube และแยกเสียงที่รันบนเครื่องของคุณ ฟรี ไม่มีโฆษณา และรวดเร็ว

- **ฟรี ไม่มีโฆษณา ไม่มีป๊อปอัป** — ดาวน์โหลดและแปลงได้มากเท่าที่ต้องการ ไม่ต้องสมัครสมาชิก ไม่มีข้อจำกัดการใช้งาน
- **อินเทอร์เฟซสะอาด ขั้นตอน 3 ขั้นตอนง่ายๆ** — วางลิงก์/เลือกไฟล์ → เลือกรูปแบบ → กดเริ่ม ผลลัพธ์พร้อมใช้ทันที
- **เลือกคุณภาพให้เหมาะกับหน้าจอ** — ตั้งแต่ 360p, 480p, 720p, 1080p จนถึง 2160p (4K) เมื่อแหล่งมี และแปลงเสียงเป็น MP3, M4A, WAV, FLAC หรือ OPUS
- **ทำงานได้ทุกอุปกรณ์ที่รัน Windows** — ไฟล์ MP4/MOV เล่นได้บนโทรศัพท์ แล็ปท็อป ทีวี และแอปมีเดียทั่วไป ส่วน ProRes ใช้กับ Adobe After Effects ได้โดยตรง
- **เป็นส่วนตัว** — ประมวลผลในเครื่อง ไฟล์และลิงก์ของคุณไม่ถูกส่งไปยังเซิร์ฟเวอร์ของ Clipora

ในวิดีโอบางรายการ ความละเอียดที่เลือกอาจไม่มีเสียงให้ เพียงเลือกตัวเลือกใกล้เคียงที่มีเสียงรวมอยู่ด้วย

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

ต้องใช้ Python 3.10+ และ Inno Setup 6 ผลลัพธ์อยู่ที่ `dist\installer` การ push tag เช่น `pc-v0.6.0` จะให้ GitHub Actions ทดสอบ สร้าง Setup และแนบ checksum ไปยัง GitHub Release อัตโนมัติ

## วิธีใช้แบบย่อ

1. เลือก **ไฟล์ในเครื่อง** หรือ **วางลิงก์**
2. เลือกโฟลเดอร์บันทึก
3. เลือกเสียง MP3/M4A/WAV/FLAC/OPUS วิดีโอ MP4/MOV หรือแยก Stem เสียง (เสียงร้อง/ดนตรี) พร้อมระดับคุณภาพและ FPS
4. สำหรับลิงก์ ให้ยืนยันว่ามีสิทธิ์ดาวน์โหลดสื่อนั้น
5. กดปุ่มเริ่ม รอผลสำเร็จ หรือกดยกเลิกได้
6. เปิดโฟลเดอร์ผลลัพธ์จากโปรแกรมได้ทันที

โหมดแยก Stem เสียงจะถามให้ติดตั้งเครื่องมือแยก Stem (ขนาดประมาณ 209 MB) ผ่านปุ่ม **เครื่องมือ** ครั้งแรก แล้วทำงานออฟไลน์ต่อได้

งานไฟล์ในเครื่องจะถามก่อนเขียนทับ ส่วนงานลิงก์จะสร้างชื่อ `(1)`, `(2)` เพื่อรักษาไฟล์เดิม และไม่แก้ไขต้นฉบับ อ่านทุกตัวเลือกใน [คู่มือผู้ใช้](docs/USER_GUIDE.md)

## เอกสาร

- [คู่มือผู้ใช้](docs/USER_GUIDE.md)
- [แก้ปัญหาและเก็บ Error Log](docs/TROUBLESHOOTING.md)
- [คู่มือพัฒนาและ Architecture](docs/DEVELOPMENT.md)
- [คู่มือสาขา Android](android/README.md)
- [ลงนาม Code Signing เพื่อลดคำเตือน SmartScreen/ไวรัส](docs/CODE_SIGNING.md)
- [แนวทางร่วมพัฒนา](CONTRIBUTING.md)
- [รายงานช่องโหว่](SECURITY.md)

## ทดสอบ

```powershell
python -m compileall -q app.py clipora tests scripts android
python -W error::ResourceWarning -m unittest discover -s tests -v
```

Integration tests สร้างสื่อขนาดเล็กใน temporary directory และ skip เมื่อไม่พบ FFmpeg

`tests/test_android_core.py` เทียบ core ฝั่ง Android กับ `clipora/` ฝั่ง PC — ถ้าแก้โมดูลฝั่ง PC ต้อง mirror มาที่ `android/core/` ด้วย ไม่งั้นเทสต์จะแจ้ง

## Roadmap ระยะใกล้

- batch processing (คิวงานหลายไฟล์)

## License

Clipora เผยแพร่ภายใต้ [GNU General Public License v3.0](LICENSE) (`GPL-3.0-only`) ผู้ที่แจกจ่ายโปรแกรมหรือเวอร์ชันดัดแปลงต้องปฏิบัติตามเงื่อนไขของ GPLv3 และจัดเตรียม source code ที่สอดคล้องกัน

Windows Setup รวม Python runtime, FFmpeg, yt-dlp และ Deno ไว้ในตัวแล้ว (~250 MB) เปิดครั้งแรกใช้งานได้ทันทีโดยไม่ต้องดาวน์โหลดเครื่องมือเพิ่ม ส่วนชุดเครื่องมือแยก Stem เสียง (PyTorch/Demucs) ติดตั้งเพิ่มครั้งแรกผ่านปุ่ม **เครื่องมือ** ดูเวอร์ชัน แหล่งที่มา checksum และ license ใน [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
