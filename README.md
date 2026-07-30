# Clipora

Clipora คือโปรแกรมเดสก์ท็อปโอเพนซอร์สสำหรับ Windows ที่ใช้แปลงไฟล์สื่อบนเครื่อง โดยไม่อัปโหลดวิดีโอไปเว็บไซต์ภายนอก ไม่มีโฆษณา ไม่มีบัญชี และไม่มีค่าประมวลผลบนเซิร์ฟเวอร์

> สถานะ: MVP สำหรับนักพัฒนาและผู้ทดลองใช้ ผู้ใช้ต้องติดตั้ง Python และ FFmpeg ก่อน

## ความสามารถปัจจุบัน

- แยกเสียงจากวิดีโอเป็น MP3 หรือ M4A
- แปลงวิดีโอเป็น MP4 แบบ H.264/AAC
- เลือกคุณภาพ High, Balanced หรือ Small
- แสดงความคืบหน้าและตรวจ stream ก่อนเริ่ม
- รองรับพาธภาษาไทย ช่องว่าง และอักขระพิเศษ
- ประมวลผลในเครื่องและไม่แก้ไขไฟล์ต้นฉบับ

รุ่นปัจจุบันรับไฟล์ในเครื่องเท่านั้น ยังไม่ใช่เครื่องมือดาวน์โหลดจาก Facebook, Instagram หรือ YouTube และไม่ได้ข้าม DRM หรือข้อจำกัดแพลตฟอร์ม

## สิ่งที่ต้องมี

| รายการ | รายละเอียด |
|---|---|
| ระบบ | Windows 10 หรือ 11 |
| Python | 3.10 ขึ้นไป พร้อม Tkinter |
| Media engine | `ffmpeg` และ `ffprobe` อยู่ใน `PATH` |
| พื้นที่ว่าง | มากพอสำหรับไฟล์ผลลัพธ์ |

Clipora ใช้ Python standard library จึงยังไม่มี runtime package เพิ่มเติม

## Clone และเปิดใช้งาน

```powershell
git clone https://github.com/ertyu007/media-toolkit-Open-source.git
cd media-toolkit-Open-source
python --version
```

ติดตั้ง FFmpeg บน Windows:

```powershell
winget install Gyan.FFmpeg
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

## วิธีใช้แบบย่อ

1. กด **เลือกไฟล์** และเลือกวิดีโอที่มีสิทธิ์ใช้งาน
2. เลือกโฟลเดอร์บันทึก
3. เลือกแยกเสียง MP3/M4A หรือแปลง MP4
4. กด **เริ่มแปลงไฟล์** และรอผลสำเร็จ
5. เปิดโฟลเดอร์ผลลัพธ์จากโปรแกรมได้ทันที

Clipora จะถามก่อนเขียนทับชื่อที่มีอยู่ และไม่แก้ไขต้นฉบับ อ่านทุกตัวเลือกใน [คู่มือผู้ใช้](docs/USER_GUIDE.md)

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

- ยกเลิกงานและลบเฉพาะ output ที่ไม่สมบูรณ์
- ตัดช่วงเวลาและ batch processing
- สร้าง Windows executable และ GitHub Releases
- เพิ่ม export presets

## License

Clipora เผยแพร่ภายใต้ [GNU General Public License v3.0](LICENSE) (`GPL-3.0-only`) ผู้ที่แจกจ่ายโปรแกรมหรือเวอร์ชันดัดแปลงต้องปฏิบัติตามเงื่อนไขของ GPLv3 และจัดเตรียม source code ที่สอดคล้องกัน

FFmpeg เป็นโครงการภายนอกและมี license ของตนเอง Clipora รุ่น source ไม่ได้รวม FFmpeg binary ผู้ใช้ติดตั้ง FFmpeg แยกต่างหาก หากมีการ bundle ในอนาคต ต้องตรวจ license และ notices ของ FFmpeg build นั้นก่อนเผยแพร่
