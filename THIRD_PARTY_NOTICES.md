# Third-party notices

Clipora เป็น GPL-3.0-only แต่ใช้หรือช่วยติดตั้งโครงการภายนอกที่มี license ของตนเอง เอกสารนี้ไม่เปลี่ยน license ของโครงการเหล่านั้นและไม่ใช่คำแนะนำทางกฎหมาย

## Runtime ที่อยู่ใน Windows build

- Python runtime — Python Software Foundation License: https://docs.python.org/3/license.html
- Tcl/Tk ซึ่งมากับ Python/Tkinter — license files อยู่ใน distribution ที่ PyInstaller รวบรวม
- PyInstaller bootloader — GPL พร้อม exception สำหรับการแจก application bundle: https://pyinstaller.org/en/stable/license.html

## เครื่องมือที่รวมอยู่ใน Windows build

เครื่องมือด้านล่างไม่ได้ถูกเก็บใน Git repository แต่ถูก staging ลงใน `dist\Clipora\tools` ระหว่าง build และรวมใน `Clipora-Setup.exe` ตัว build ดาวน์โหลดผ่าน HTTPS จาก release URL ที่ pin ไว้ ตรวจ SHA-256 ก่อนติดตั้ง โปรแกรมสามารถค้นหาเครื่องมือเหล่านี้ได้โดยไม่ต้องดาวน์โหลดตอนเปิดครั้งแรก และสามารถดาวน์โหลดใหม่ไปยัง `%LOCALAPPDATA%\Clipora\tools` ได้ผ่านปุ่ม **เครื่องมือ** ในแอป

### FFmpeg Essentials 8.1.2

- Binary publisher: GyanD
- Download: https://github.com/GyanD/codexffmpeg/releases/download/8.1.2/ffmpeg-8.1.2-essentials_build.zip
- SHA-256: `db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec`
- Corresponding FFmpeg source commit: https://github.com/FFmpeg/FFmpeg/commit/38b88335f9
- License guidance: https://ffmpeg.org/legal.html

### yt-dlp 2026.07.04

- Download: https://github.com/yt-dlp/yt-dlp/releases/download/2026.07.04/yt-dlp.exe
- SHA-256: `52fe3c26dcf71fbdc85b528589020bb0b8e383155cfa81b64dd447bbe35e24b8`
- Source: https://github.com/yt-dlp/yt-dlp/tree/2026.07.04
- License and bundled third-party notices: https://github.com/yt-dlp/yt-dlp/releases/tag/2026.07.04

### Deno 2.8.1

- Download: https://github.com/denoland/deno/releases/download/v2.8.1/deno-x86_64-pc-windows-msvc.zip
- SHA-256: `5fb5bac71f609fb91ec8960fb290885aadc27eeb22f07a8eca0c3db6be38b11a`
- Source: https://github.com/denoland/deno/tree/v2.8.1
- License: https://github.com/denoland/deno/blob/v2.8.1/LICENSE.md

## การอัปเดต manifest

ผู้ดูแลต้องใช้ immutable release URL ตรวจ checksum จากผู้เผยแพร่ อัปเดตเวอร์ชัน/source/license พร้อมกัน เพิ่ม regression test และทดสอบ clean-machine ก่อน release ห้ามเปลี่ยนเป็น URL แบบ latest โดยไม่มี checksum ที่ตรงกับ asset นั้น
