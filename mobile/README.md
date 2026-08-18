# Clipora Mobile

แอปมือถือ Android ของ Clipora — ประมวลผลในเครื่องมือถือเอง ฟรี 100% ไม่ต้องใช้คอมพิวเตอร์ ไม่มีค่าโฮสติ้ง ไม่มีโฆษณา

## ความสามารถ

- **ดาวน์โหลดลิงก์** — วาง URL สาธารณะจาก YouTube, Facebook, Instagram และเว็บที่ yt-dlp รองรับ เลือกดาวน์โหลดวิดีโอ (mp4/mov, คุณภาพสูงสุด-360p, เฟรมเรต) หรือเฉพาะเสียง (mp3/m4a/wav/flac/opus)
- **แปลงไฟล์ในเครื่อง** — เลือกวิดีโอในโทรศัพท์ **ครั้งละหลายไฟล์ได้ (batch)** แปลงเป็น MP4/MOV (ProRes) หรือแยกเสียง (mp3/m4a/wav/flac/opus)
- **แก้ไข metadata เพลง** — แก้ชื่อเพลง ศิลปิน อัลบั้ม แนวเพลง ลำดับแทร็ก ปี และแนบ/เปลี่ยนหน้าปกของไฟล์ mp3/m4a/flac/opus โดยไม่ต้องแปลงไฟล์ใหม่ (copy stream)
- ผลลัพธ์ถูกบันทึกไปยังโฟลเดอร์ **Downloads/Clipora** อัตโนมัติ พร้อมปุ่มแชร์
- แสดงความคืบหน้าแบบเรียลไทม์ ยกเลิกงานได้ (รวมทั้งยกเลิกทั้ง batch)
- หน้าจอภาษาไทย

## สิ่งที่ฝังอยู่ในแอป

| ไลบรารี | ใช้ทำอะไร |
|---|---|
| `ffmpeg_kit_flutter_new` (FFmpeg v8.1.2 Full-GPL) | แปลงไฟล์ / แยกเสียง / ffprobe |
| `yt-dlp-android` (AAR ที่ build เอง: Python 3.13 + yt-dlp 2026.7.4 + curl-cffi 0.15.0) | ดาวน์โหลดลิงก์ 1,000+ เว็บไซต์ |
| `quickjs` (qjs arm64 ที่ cross-compile จาก NDK) | JS runtime สำหรับแก้ JS challenge ของ YouTube (จำเป็นต่อการโหลดวิดีโอตัวจริง) |

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
- **yt-dlp ไม่อัปเดตในแอป** — เว็บเปลี่ยนสัญญาณบ่อย ถ้าเวอร์ชันเก่าเกินไป ให้ rebuild AAR (ดูด้านล่าง) แล้ว build APK ใหม่
- **AAR ที่ฝัง curl-cffi build เองจาก [ffmpegkit-maintained/yt-dlp-android](https://github.com/ffmpegkit-maintained/yt-dlp-android) (MIT)** — เพิ่ม `curl-cffi==0.15.0` + `cffi==1.17.1` + `pycparser` + `chaquopy-libffi` ใน pip block ของ `library/build.gradle` (ใช้ `options "--no-deps"` เพราะ mirror ของ Chaquopy ยังไม่มี cffi 2.x) และแก้ `library/src/main/python/ytdlp_runner.py` ให้ map flag `--impersonate` (แปลงเป็น `ImpersonateTarget`) + `--js-runtimes` แล้วรัน `gradlew :library:assembleRelease` → นำไฟล์ `library-release.aar` ไปวางที่ `android/app/libs/yt-dlp-android-curl.aar`
- **`qjs` (QuickJS) ที่ฝังใน `assets/qjs/arm64-v8a/`** — cross-compile จาก [bellard/quickjs](https://github.com/bellard/quickjs) ด้วย NDK clang (เช่น `aarch64-linux-android24-clang qjs.c quickjs.c dtoa.c libregexp.c libunicode.c cutils.c quickjs-libc.c -o qjs` + stub `repl`) แล้ว app extract ไปยัง filesDir ผ่าน `MainActivity.ensureJsRuntime()` และส่ง `--js-runtimes quickjs:<path>`
- ใช้สิทธิ์ดาวน์โหลดเฉพาะสื่อที่คุณเป็นเจ้าของ ได้รับอนุญาต หรืออยู่ในสาธารณสมบัติเท่านั้น

## โครงสร้างโค้ด

```text
lib/
  main.dart              entry + theme
  app_state.dart         ควบคุมงานดาวน์โหลด/แปลง/metadata + จัดการ state
  models/
    job.dart             โมเดลงาน (รองรับ batch)
    media_metadata.dart  โมเดล metadata เพลง
  services/
    ytdlp.dart           MethodChannel เรียก yt-dlp ฝั่ง Android
    media.dart           ffmpeg/ffprobe (probe, แปลง, merge, remux, อ่าน/เขียน metadata)
    native.dart          เลือกไฟล์ (เดี่ยว/หลายไฟล์/รูป) + บันทึกลง Downloads
  screens/
    home_screen.dart     หน้าแรก (ลิงก์ / ไฟล์ / รายการงาน)
    metadata_editor.dart แก้ไข metadata เพลง
    video_preview.dart   หน้าตัวอย่างวิดีโอ
  widgets/
    ui.dart              คอมโพเนนต์ร่วม (การ์ด, ปุ่ม, dropdown)
android/app/src/main/kotlin/.../MainActivity.kt
                          MethodChannel + EventChannel + MediaStore + pick ไฟล์/รูปหลายแบบ
```