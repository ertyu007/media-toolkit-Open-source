# Clipora

Clipora คือโปรแกรมเดสก์ท็อปโอเพนซอร์สสำหรับ Windows สำหรับดาวน์โหลดสื่อสาธารณะที่ได้รับอนุญาต แยกเสียง และแปลงวิดีโอ โดยไม่มีโฆษณา ไม่มีบัญชี Clipora และไม่มีค่าประมวลผลบนเซิร์ฟเวอร์ ไฟล์ในเครื่องจะไม่ถูกอัปโหลด ส่วนโหมดลิงก์เชื่อมต่อเว็บไซต์ต้นทางผ่าน `yt-dlp` แล้วประมวลผลผลลัพธ์บนเครื่อง

พัฒนาโดย [ertyu.dev](https://ertyu.dev)

Clipora ประกอบด้วย **สองผลิตภัณฑ์แยกกันใน repository เดียว** — เวอร์ชัน แพ็กเกจ และ release แยกกันโดยสิ้นเชิง:

| ผลิตภัณฑ์ | เทคโนโลยี | release tag | เอกสาร |
|---|---|---|---|
| **Clipora PC** — เดสก์ท็อป Windows | Python/Tkinter | `pc-vX.Y.Z` | [คู่มือผู้ใช้](docs/USER_GUIDE.md) |
| **Clipora Mobile** — แอป Android | Flutter | `mobile-vX.Y.Z` | [mobile/README.md](mobile/README.md) |

ดาวน์โหลดไฟล์แต่ละฝั่งจากหน้า [GitHub Releases](https://github.com/ertyu007/media-toolkit-Open-source/releases) โดยเลือก tag ตามฝั่ง — release ของ PC อยู่ที่ `pc-v*` และของมือถืออยู่ที่ `mobile-v*`

---

# Clipora PC (เดสก์ท็อป Windows)

> รุ่น 0.4 เพิ่ม Windows installer และ Setup Assistant ผู้ใช้ทั่วไปไม่ต้องติดตั้ง Python หรือแก้ PATH เอง
>
> รุ่น 0.5+ ตัวติดตั้งรวม FFmpeg, yt-dlp และ Deno ไว้ในตัวแล้ว เปิดครั้งแรกใช้งานได้ทันทีโดยไม่ต้องดาวน์โหลดเครื่องมือเพิ่ม
>
> รุ่น 0.5.1 เพิ่มการแยกสเต็มเสียง (เสียงร้อง/ดนตรี) บนเครื่อง และปุ่มอัปเดต yt-dlp ในแอป
>
> รุ่น 0.5.2 แก้ปุ่มโดเนทให้แสดง QR PromptPay ได้ และใช้รูป QR ที่ commit ใน repo ตรง ๆ (ไม่พึ่ง secret ใน CI)
>
> รุ่น 0.5.6 เมื่อโดนบล็อกการดาวน์โหลด (HTTP 403/429 หรือกัน bot) แอปจะลองซ้ำอัตโนมัติด้วยวิธีที่เพิ่มขึ้น (header เฉพาะเว็บ, สลับ player client YouTube, จำลองเบราว์เซอร์) อัปเดต yt-dlp ให้อัตโนมัติตอนเปิดแอป และแจ้งเตือนเมื่อถูกบล็อกระดับเครือข่าย/ISP (เปลี่ยน DNS หรือใช้ VPN)
>
> รุ่น 0.6.0 เปลี่ยน UI/UX ครั้งใหญ่ (ธีม Midnight Amethyst, stepper 3 ขั้น, result panel, dialog เขียนทับ) และเพิ่มความปลอดภัย (กัน zip-slip ตอนติดตั้งเครื่องมือ, ยืนยันสิทธิ์สื่อก่อนดาวน์โหลดทุกครั้ง)

## ติดตั้งสำหรับผู้ใช้ทั่วไป

1. เปิดหน้า [GitHub Releases](https://github.com/ertyu007/media-toolkit-Open-source/releases) แล้วเลือก tag `pc-v<เวอร์ชัน>`
2. ดาวน์โหลด `Clipora-Setup-<version>-x64.exe` และไฟล์ `.sha256` ที่อยู่คู่กัน (หรือเลือก `Clipora-<version>-x64.zip` แบบพกพาได้ ไม่ต้องติดตั้ง แค่แกะ zip แล้วรัน `Clipora.exe`)
3. เปิดตัวติดตั้ง เลือกสร้างไอคอนบน Desktop ได้ตามต้องการ ไม่ต้องใช้สิทธิ์ Administrator
4. เปิด Clipora แล้วใช้งานได้ทันที ไม่ต้องดาวน์โหลดเครื่องมือเพิ่ม

ไฟล์ Setup รวม Python/Tkinter และ FFmpeg, yt-dlp, Deno ไว้ในตัว (ขนาดตัวติดตั้งประมาณ 250 MB) ตัวช่วยตั้งค่า (Setup Assistant) จะแสดงเฉพาะเมื่อเครื่องมือบางตัวหายหรือผู้ใช้เลือก **เครื่องมือ → ติดตั้งใหม่ / ซ่อมเครื่องมือ** เท่านั้น

## ความสามารถปัจจุบัน

- วางลิงก์สาธารณะจาก YouTube, Facebook, Instagram และเว็บไซต์ที่ yt-dlp รองรับ
- ดาวน์โหลดวิดีโอแบบคุณภาพสูงสุด, 2160p (4K), 1080p, 720p, 480p หรือ 360p
- ดาวน์โหลดเฉพาะเสียงเป็น MP3, M4A, WAV, FLAC หรือ OPUS
- แยกเสียงจากวิดีโอเป็น MP3, M4A, WAV, FLAC หรือ OPUS
- **แยกสเต็มเสียง** (เสียงร้อง + ดนตรี และสเต็มอื่นๆ) บนเครื่องด้วย Demucs โดยไม่ต้องเชื่อมอินเทอร์เน็ต พร้อมไฟล์ `_stems.zip` รวมทุกสเต็ม
- **อัปเดต yt-dlp** ภายในแอป ตรวจอัตโนมัติตอนเปิด และตรวจ checksum จากผู้เผยแพร่ทุกครั้ง
- แปลงวิดีโอเป็น MP4 แบบ H.264/AAC
- แปลงวิดีโอเป็น MOV แบบ ProRes 422 (รองรับการ import ใน Adobe After Effects)
- เลือกเฟรมเรตสูงสุดของผลลัพธ์ได้ (สูงสุด, 60fps หรือ 30fps)
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

ต้องใช้ Python 3.10+ และ Inno Setup 6 ผลลัพธ์อยู่ที่ `dist\installer` การ push tag เช่น `pc-v0.6.0` (PC) หรือ `mobile-v1.0.4` (Android) จะให้ GitHub Actions ทดสอบ สร้าง Setup และแนบ checksum ไปยัง GitHub Release อัตโนมัติ

## วิธีใช้แบบย่อ

1. เลือก **ไฟล์ในเครื่อง** หรือ **วางลิงก์**
2. เลือกโฟลเดอร์บันทึก
3. เลือกเสียง MP3/M4A/WAV/FLAC/OPUS วิดีโอ MP4/MOV หรือแยกสเต็มเสียง (เสียงร้อง/ดนตรี) พร้อมระดับคุณภาพและเฟรมเรต
4. สำหรับลิงก์ ให้ยืนยันว่ามีสิทธิ์ดาวน์โหลดสื่อนั้น
5. กดปุ่มเริ่ม รอผลสำเร็จ หรือกดยกเลิกได้
6. เปิดโฟลเดอร์ผลลัพธ์จากโปรแกรมได้ทันที

โหมดแยกสเต็มเสียงจะถามให้ติดตั้งเครื่องมือแยกสเต็ม (ขนาดประมาณ 209 MB) ผ่านปุ่ม **เครื่องมือ** ครั้งแรก แล้วทำงานออฟไลน์ต่อได้

งานไฟล์ในเครื่องจะถามก่อนเขียนทับ ส่วนงานลิงก์จะสร้างชื่อ `(1)`, `(2)` เพื่อรักษาไฟล์เดิม และไม่แก้ไขต้นฉบับ อ่านทุกตัวเลือกใน [คู่มือผู้ใช้](docs/USER_GUIDE.md)

## เอกสาร (PC)

- [คู่มือผู้ใช้](docs/USER_GUIDE.md)
- [แก้ปัญหาและเก็บ Error Log](docs/TROUBLESHOOTING.md)
- [คู่มือพัฒนาและ Architecture](docs/DEVELOPMENT.md)
- [ลงนาม Code Signing เพื่อลดคำเตือน SmartScreen/ไวรัส](docs/CODE_SIGNING.md)
- [แนวทางร่วมพัฒนา](CONTRIBUTING.md)
- [รายงานช่องโหว่](SECURITY.md)

## ทดสอบ

```powershell
python -m compileall -q app.py clipora tests scripts
python -W error::ResourceWarning -m unittest discover -s tests -v
```

Integration tests สร้างสื่อขนาดเล็กใน temporary directory และ skip เมื่อไม่พบ FFmpeg

## Roadmap ระยะใกล้ (PC)

- ตัดช่วงเวลาและ batch processing
- Portable ZIP (ไฟล์พกพารวมเครื่องมือทั้งหมด)

---

# Clipora Mobile (แอป Android)

แอปมือถือของ Clipora สำหรับ Android — ประมวลผลในเครื่องมือถือเอง ฟรี 100% ไม่มีค่าโฮสติ้ง ไม่มีโฆษณา

## ความสามารถ

- **ดาวน์โหลดลิงก์** — วาง URL สาธารณะจาก YouTube, Facebook, Instagram และเว็บที่ yt-dlp รองรับ เลือกวิดีโอหรือเฉพาะเสียง พร้อมเฟรมเรตและคุณภาพ
- **แปลงไฟล์ในเครื่อง** — เลือกวิดีโอในโทรศัพท์ แปลงเป็น MP4/MOV (ProRes) หรือแยกเสียง
- ผลลัพธ์ถูกบันทึกไปยังโฟลเดอร์ **Downloads/Clipora** อัตโนมัติ พร้อมปุ่มแชร์ และแสดงความคืบหน้าแบบเรียลไทม์ ยกเลิกงานได้
- หน้าจอภาษาไทย ฟรี ไม่มีโฆษณา และไม่มีการอัปโหลดไฟล์

## ติดตั้งสำหรับผู้ใช้ทั่วไป

1. เปิดหน้า [GitHub Releases](https://github.com/ertyu007/media-toolkit-Open-source/releases) แล้วเลือก tag `mobile-v<เวอร์ชัน>`
2. ดาวน์โหลด `app-arm64-v8a-release.apk` และไฟล์ `.sha256` ที่อยู่คู่กัน
3. เปิดไฟล์บนมือถือ → ยอมให้ติดตั้งจากแหล่งที่ไม่รู้จัก → ติดตั้ง

> ใช้ตัว **arm64-v8a** (มือถือรุ่นใหม่เกือบทั้งหมด) — `armeabi-v7a` ใช้ไม่ได้เพราะ yt-dlp รองรับแค่ arm64/x86_64

## สิ่งที่ฝังอยู่ในแอป

| ไลบรารี | ใช้ทำอะไร |
|---|---|
| `ffmpeg_kit_flutter_new` (FFmpeg v8.1.2 Full-GPL) | แปลงไฟล์ / แยกเสียง / ffprobe |
| `yt-dlp-android` (AAR ที่ build เอง: Python 3.13 + yt-dlp + curl-cffi) | ดาวน์โหลดลิงก์ 1,000+ เว็บไซต์ |
| `quickjs` (qjs arm64 ที่ cross-compile จาก NDK) | JS runtime สำหรับแก้ JS challenge ของ YouTube |

## วิธี build เอง

```powershell
cd mobile
flutter pub get
flutter build apk --release --split-per-abi
```

ต้องมี Flutter SDK + Android SDK ก่อน ผลลัพธ์อยู่ที่ `mobile/build/app/outputs/flutter-apk/app-arm64-v8a-release.apk`

## ข้อควรรู้

- **Android เท่านั้น** — iOS ทำไม่ได้เพราะ Apple ห้ามฝัง Python interpreter ลงแอป
- **yt-dlp ไม่อัปเดตในแอป** — ถ้าเวอร์ชันเก่าเกินไปต้อง rebuild AAR แล้ว build APK ใหม่ ดูขั้นตอนใน [mobile/README.md](mobile/README.md)
- ใช้สิทธิ์ดาวน์โหลดเฉพาะสื่อที่คุณเป็นเจ้าของ ได้รับอนุญาต หรืออยู่ในสาธารณสมบัติเท่านั้น

## License

Clipora เผยแพร่ภายใต้ [GNU General Public License v3.0](LICENSE) (`GPL-3.0-only`) ผู้ที่แจกจ่ายโปรแกรมหรือเวอร์ชันดัดแปลงต้องปฏิบัติตามเงื่อนไขของ GPLv3 และจัดเตรียม source code ที่สอดคล้องกัน

Windows Setup รวม Python runtime แต่ไม่รวม FFmpeg, yt-dlp หรือ Deno ตัว Setup Assistant ดาวน์โหลดจากผู้เผยแพร่โดยตรง ส่วนชุดเครื่องมือแยกสเต็มเสียง (PyTorch/Demucs) ผู้ใช้ติดตั้งครั้งแรกผ่านปุ่ม **เครื่องมือ** ดูเวอร์ชัน แหล่งที่มา checksum และ license ใน [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)
