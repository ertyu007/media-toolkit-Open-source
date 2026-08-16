# Clipora Mobile

แอปมือถือ Android ของ Clipora — ประมวลผลในเครื่องมือถือเอง ฟรี 100% ไม่ต้องใช้คอมพิวเตอร์ ไม่มีค่าโฮสติ้ง ไม่มีโฆษณา

## ความสามารถ

- **ดาวน์โหลดลิงก์** — วาง URL สาธารณะจาก YouTube, Facebook, Instagram และเว็บที่ yt-dlp รองรับ เลือกดาวน์โหลดวิดีโอ (mp4/mov, คุณภาพสูงสุด-360p, เฟรมเรต) หรือเฉพาะเสียง (mp3/m4a/wav/flac/opus)
- **แปลงไฟล์ในเครื่อง** — เลือกวิดีโอในโทรศัพท์ แปลงเป็น MP4/MOV (ProRes) หรือแยกเสียง (mp3/m4a/wav/flac/opus)
- ผลลัพธ์ถูกบันทึกไปยังโฟลเดอร์ **Downloads/Clipora** อัตโนมัติ พร้อมปุ่มแชร์
- แสดงความคืบหน้าแบบเรียลไทม์ ยกเลิกงานได้
- หน้าจอภาษาไทย

## สิ่งที่ฝังอยู่ในแอป

| ไลบรารี | ใช้ทำอะไร |
|---|---|
| `ffmpeg_kit_flutter_new` (FFmpeg v8.1.2 Full-GPL) | แปลงไฟล์ / แยกเสียง / ffprobe |
| `yt-dlp-android` (Python 3.13 + yt-dlp ฝังใน AAR) | ดาวน์โหลดลิงก์ 1,000+ เว็บไซต์ |

ทุกอย่างประมวลผลบนเครื่องมือถือ ไม่มีการอัปโหลดไฟล์ไปที่ไหน

## วิธีติดตั้ง

ดาวน์โหลดไฟล์ **`app-arm64-v8a-release.apk`** (อยู่ที่ `build/app/outputs/flutter-apk/`) แล้วเปิดไฟล์บนมือถือ → ยอมให้ติดตั้งจากแหล่งที่ไม่รู้จัก → ติดตั้ง

> ใช้ตัว **arm64-v8a** (มือถือรุ่นใหม่เกือบทั้งหมด) — `armeabi-v7a` ใช้ไม่ได้เพราะ yt-dlp รองรับแค่ arm64/x86_64

## วิธี build เอง

ต้องมี Flutter SDK + Android SDK ก่อน:

```powershell
flutter pub get
flutter build apk --release --split-per-abi
```

## ข้อควรรู้

- **Android เท่านั้น** — iOS ทำไม่ได้เพราะ Apple ห้ามฝัง Python interpreter ลงแอป
- **yt-dlp ไม่อัปเดตในแอป** — เว็บเปลี่ยนสัญญาณบ่อย เช็กเวอร์ชันใหม่ได้ด้วย `powershell -ExecutionPolicy Bypass -File tools\check_ytdlp_update.ps1` ถ้ามีเวอร์ชันใหม่ ให้แก้เวอร์ชัน `dev.ffmpegkit-maintained:yt-dlp-android` ใน `android/app/build.gradle.kts` แล้ว build ใหม่
- ใช้สิทธิ์ดาวน์โหลดเฉพาะสื่อที่คุณเป็นเจ้าของ ได้รับอนุญาต หรืออยู่ในสาธารณสมบัติเท่านั้น

## โครงสร้างโค้ด

```text
lib/
  main.dart              UI (Material 3 ธีมเข้ม ภาษาไทย)
  app_state.dart         ควบคุมงานดาวน์โหลด/แปลง + จัดการ state
  models/job.dart        โมเดลงาน
  services/
    ytdlp.dart           MethodChannel เรียก yt-dlp ฝั่ง Android
    media.dart           ffmpeg/ffprobe (probe, แปลง, merge, remux)
    native.dart          เลือกไฟล์ + บันทึกลง Downloads
android/app/src/main/kotlin/.../MainActivity.kt
                          MethodChannel + EventChannel + MediaStore
```