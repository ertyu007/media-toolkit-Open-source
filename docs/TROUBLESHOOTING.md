# คู่มือแก้ปัญหา Clipora

## สารบัญ

1. ตรวจพื้นฐาน
2. Python และ Tkinter
3. FFmpeg และ PATH
4. Input และ stream
5. Output และ permission
6. Progress และ performance
7. Codec/encoder
8. เก็บ Error Log
9. เปิด Issue ที่มีประโยชน์

## 1. ตรวจพื้นฐาน

หากติดตั้งจาก `Clipora-Setup.exe` ให้เปิดปุ่ม **เครื่องมือ** ในโปรแกรมก่อน แล้วเลือกติดตั้งหรือซ่อมใหม่ ผู้ใช้ Setup ไม่ต้องใช้ Python หรือแก้ PATH

นักพัฒนาที่รันจาก source ให้เปิด PowerShell ในโฟลเดอร์ที่มี `app.py`:

```powershell
python scripts/check_environment.py
python -m unittest discover -s tests -v
```

จดหัวข้อที่ FAIL และแก้จากบนลงล่าง อย่าติดตั้ง package แบบสุ่ม

### Setup Assistant ดาวน์โหลดไม่สำเร็จ

- ตรวจอินเทอร์เน็ต firewall, proxy และพื้นที่ว่าง
- กด **เครื่องมือ → ติดตั้งใหม่ / ซ่อมเครื่องมือ**
- โปรแกรมดาวน์โหลดผ่าน HTTPS และไม่ยอมติดตั้งไฟล์ที่ checksum ไม่ตรง
- หากขึ้น `checksum ไม่ตรง` อย่าฝืนรันไฟล์ ให้เปิด issue พร้อมชื่อเครื่องมือและข้อความผิดพลาด แต่ห้ามแนบไฟล์ executable ที่สงสัย
- ไฟล์ชั่วคราวของงานที่ล้มเหลวจะถูกล้าง เครื่องมือเดิมที่ใช้งานได้จะไม่ถูกแทนที่ก่อนตรวจครบ

## 2. Python และ Tkinter

### `python` ไม่เป็นคำสั่ง

สาเหตุ: ยังไม่ติดตั้ง หรือ Python ไม่อยู่ใน PATH

ตรวจ:

```powershell
Get-Command python
py --version
```

หาก `py` ใช้ได้แต่ `python` ไม่ได้ สามารถลอง:

```powershell
py app.py
```

ติดตั้ง Python 3.10+ และเปิด terminal ใหม่ อย่าดาวน์เกรด source code เพื่อหลบ requirement โดยไม่แก้เอกสารและ test matrix

### Python ต่ำกว่า 3.10

`check_environment.py` จะแสดง FAIL ให้ติดตั้งเวอร์ชันที่รองรับและตรวจว่า `Get-Command python` ชี้ executable ที่ถูกต้อง

### `No module named tkinter`

ติดตั้ง Python distribution ที่รวม Tcl/Tk หรือแก้ Python installation แล้วเปิด terminal ใหม่ ตรวจด้วย:

```powershell
python -c 'import tkinter; print(tkinter.TkVersion)'
```

## 3. FFmpeg และ PATH

### `ไม่พบ FFmpeg`

รุ่น Setup: เปิด **เครื่องมือ** แล้วกดติดตั้ง/ซ่อม Clipora จะเก็บ `ffmpeg.exe` และ `ffprobe.exe` ใน `%LOCALAPPDATA%\Clipora\tools`

รุ่น source ตรวจ PATH:

ตรวจ:

```powershell
Get-Command ffmpeg
Get-Command ffprobe
```

ติดตั้ง:

```powershell
winget install Gyan.FFmpeg
```

ปิดทั้ง PowerShell และ Clipora แล้วเปิดใหม่ เพราะ process เดิมไม่เห็น PATH ที่เพิ่งเปลี่ยน

### พบ ffmpeg แต่ไม่พบ ffprobe

Clipora ต้องใช้ทั้งคู่จาก FFmpeg distribution เดียวกัน ตรวจว่า directory `bin` มี `ffmpeg.exe` และ `ffprobe.exe` และ directory นั้นอยู่ใน PATH

### มี FFmpeg หลายเวอร์ชัน

```powershell
Get-Command ffmpeg -All
Get-Command ffprobe -All
ffmpeg -version
ffprobe -version
```

จัด PATH ให้คู่ที่ต้องการมาก่อน หลีกเลี่ยง ffmpeg กับ ffprobe คนละ distribution/version

### `ไม่พบ yt-dlp`

รุ่น Setup: ใช้เมนู **เครื่องมือ** โดยไม่ต้องเปิด PowerShell

รุ่น source ตรวจและติดตั้ง:

ตรวจและติดตั้ง:

```powershell
Get-Command yt-dlp
winget install yt-dlp.yt-dlp
winget install DenoLand.Deno
yt-dlp --version
deno --version
```

เปิด PowerShell และ Clipora ใหม่หลังติดตั้ง หากเว็บไซต์ที่เคยใช้ได้เริ่มล้มเหลว ให้อัปเดตจากช่องทางติดตั้งเดิม หรือใช้ `yt-dlp -U` เมื่อเป็น official release binary

หาก WinGet ใช้งานไม่ได้ สามารถวาง official `yt-dlp.exe` ไว้ที่ `%LOCALAPPDATA%\\Clipora\\bin\\yt-dlp.exe` ได้ Clipora จะตรวจตำแหน่งนี้โดยไม่ต้องแก้ PATH ควรดาวน์โหลดจากหน้า release ทางการและตรวจ checksum ก่อนใช้งาน

หาก YouTube แจ้งว่าไม่พบ JavaScript runtime ให้ติดตั้ง Deno หรือ Node.js แล้วเปิดโปรแกรมใหม่ Clipora จะส่ง runtime ที่พบให้ yt-dlp โดยอัตโนมัติ

### ดาวน์โหลดลิงก์ไม่สำเร็จ

- ตรวจว่าลิงก์เปิดแบบสาธารณะได้และเป็นรายการเดียว ไม่ใช่ playlist/live
- Clipora ไม่รับ login, cookies, private/paid media หรือ DRM
- อัปเดต yt-dlp เพราะเว็บไซต์เปลี่ยน extractor บ่อย
- ลองลิงก์สาธารณะที่ผู้ใช้เป็นเจ้าของหรือได้รับอนุญาต
- อย่าโพสต์ private URL, signed URL, token หรือข้อมูลบัญชีใน issue

## 4. Input และ stream

### โปรแกรมบอกว่าไม่พบไฟล์ต้นฉบับ

- ตรวจว่าไฟล์ยังอยู่หลังเลือก
- อย่าย้าย/เปลี่ยนชื่อ/ถอด external drive ระหว่างงาน
- ลองคัดลอกไฟล์ไปยังโฟลเดอร์ local ที่พาธสั้น

### `ไฟล์นี้ไม่มีเสียงให้แยก`

ไฟล์ไม่มี audio stream หรือ probe อ่านไม่ได้ ตรวจ:

```powershell
ffprobe -v error -show_streams -of json 'C:\path\to\input.mp4'
```

มองหา `codec_type` ที่เป็น `audio` อย่าเปลี่ยน extension เพื่อทำให้ไฟล์ดูเหมือนมีเสียง

### `ไฟล์นี้ไม่มีภาพวิดีโอสำหรับแปลง`

ไฟล์อาจเป็น audio-only, เสียหาย หรือ codec ไม่รองรับ ตรวจ stream ด้วย ffprobe เช่นเดียวกัน

### ไฟล์เปิดใน player ได้แต่ Clipora ไม่ได้

Player อาจมี decoder ที่ FFmpeg build นี้ไม่มี เก็บ ffprobe output และ FFmpeg version แล้วเปิด issue โดยตัดพาธส่วนตัวออก

## 5. Output และ permission

### เขียนไฟล์ไม่ได้

- เลือก Downloads, Videos หรือโฟลเดอร์ของผู้ใช้
- หลีกเลี่ยง `C:\Windows`, `Program Files` และ network drive ที่ไม่มีสิทธิ์
- ตรวจว่า destination ยังเชื่อมต่ออยู่
- ตรวจว่า output ไม่ถูกเปิดล็อกโดยโปรแกรมอื่น
- ไม่ควรแก้ด้วยการเปิด Administrator เป็นวิธีแรก

### พื้นที่ไม่พอ

```powershell
Get-PSDrive -PSProvider FileSystem
```

เพิ่มพื้นที่หรือเลือก drive อื่น Output High อาจใหญ่กว่าที่คาดตามความซับซ้อนของวิดีโอ

### มี output เดิม

Clipora จะถามก่อน overwrite หากต้องการเก็บทั้งคู่ ให้กด No แล้วเปลี่ยนชื่อ/ย้ายของเดิมหรือเลือก destination ใหม่

### มีไฟล์ output หลังงานล้มเหลว

Clipora เขียนลงไฟล์ชั่วคราวที่มี `.clipora-` ในชื่อและลบไฟล์นั้นหลังยกเลิกหรือเกิด error หากยังเหลือไฟล์ชั่วคราว แสดงว่า cleanup ถูกขัดขวาง เช่น permission หรือโปรแกรมหยุดแบบไม่ปกติ ปิดโปรแกรมที่ล็อกไฟล์แล้วลบเฉพาะไฟล์ `.clipora-` ที่ตรวจแล้วว่าเป็น partial output ห้ามลบ source หรือทั้ง destination directory

## 6. Progress และ performance

### Progress ไม่ขยับ

- บางไฟล์ไม่มี duration ที่เชื่อถือได้
- ตรวจ Task Manager ว่า FFmpeg ใช้ CPU/disk อยู่หรือไม่
- รอไฟล์ยาว/ความละเอียดสูง
- หาก UI ค้างทั้งหมด ให้เก็บ input metadata และขั้นตอนทำซ้ำ

### เครื่องช้าหรือร้อน

Encoding ใช้ CPU สูงเป็นปกติ ปิดงานหนักอื่น วางเครื่องให้ระบายอากาศ และใช้ Balanced/Small ตามความต้องการ รุ่นนี้ประมวลผลทีละไฟล์

### Progress ถึง 100 แต่ไม่มีไฟล์

Core ปัจจุบันตรวจ target existence และขนาดก่อน success หากยังพบ ให้เก็บ exact message, FFmpeg version, destination type และ test results

## 7. Codec และ encoder

### `Unknown encoder libx264`

FFmpeg build ไม่มี `libx264` ซึ่งจำเป็นต่อ MP4 ปัจจุบัน ตรวจ:

```powershell
ffmpeg -hide_banner -encoders | Select-String libx264
```

ใช้ FFmpeg build ที่มี encoder นี้ อย่าเปลี่ยน command ไป codec อื่นโดยไม่เพิ่ม quality mapping และ integration tests

### `Unknown encoder libmp3lame`

ตรวจ:

```powershell
ffmpeg -hide_banner -encoders | Select-String libmp3lame
```

ติดตั้ง build ที่รองรับ หรือใช้ M4A ชั่วคราวหาก AAC encoder พร้อม

### Output คุณภาพต่ำกว่าต้นฉบับ

MP3, M4A และ MP4 ปัจจุบันมีการ re-encode จึงมีการสูญเสีย เลือก High สำหรับ MP4 แต่ไม่สามารถคืนรายละเอียดที่ต้นฉบับไม่มีได้

## 8. เก็บ Error Log

ก่อนเปิด issue ให้เก็บ:

```powershell
python --version
ffmpeg -version
ffprobe -version
python scripts/check_environment.py
python -W error::ResourceWarning -m unittest discover -s tests -v
```

บันทึกเพิ่มเติม:

- Operation: MP3, M4A หรือ MP4
- Quality ที่เลือก
- Container/codec/stream จาก ffprobe
- ขั้นตอนทำซ้ำทีละข้อ
- ข้อความ error แบบเต็ม
- ปัญหาเกิดทุกไฟล์หรือไฟล์เดียว

ลบหรือแทนที่ข้อมูลต่อไปนี้ก่อนโพสต์สาธารณะ:

- ชื่อจริง ชื่อผู้ใช้ และพาธ home
- ชื่อไฟล์ที่เปิดเผยลูกค้า/งานส่วนตัว
- URL ส่วนตัว token cookie หรือ credential
- media ที่ไม่มีสิทธิ์เผยแพร่

อย่าอัปโหลดไฟล์ต้นฉบับที่เป็นความลับ ใช้ fixture ที่สร้างใหม่หรือคลิปสั้นที่อนุญาตแทน

## 9. เปิด Issue ที่มีประโยชน์

ใช้รูปแบบ:

```text
Summary:
Expected:
Actual:
Steps to reproduce:
Python version:
FFmpeg/ffprobe version:
Operation and settings:
Input stream summary:
Exact error:
Tests run:
Sensitive data removed: yes/no
```

หนึ่ง issue ควรมีหนึ่งปัญหาหลัก ระบุสิ่งที่ลองแล้ว และอย่าแนบ screenshot เพียงอย่างเดียวหากสามารถคัดลอก error text ได้
