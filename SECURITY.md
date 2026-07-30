# Security Policy

## Supported versions

Clipora ยังอยู่ในช่วงก่อน release แรก จึงรองรับเฉพาะ revision ล่าสุดบน branch หลัก เมื่อเริ่มออก releases จะเพิ่มตารางเวอร์ชันที่รับ security updates

## Reporting a vulnerability

อย่าเปิด public issue ที่มีขั้นตอน exploit, malicious media, credential หรือข้อมูลที่ทำให้ผู้ใช้เสี่ยง

ก่อน GitHub repository เปิดสาธารณะ ให้ติดต่อ maintainer ผ่านช่องทางส่วนตัวที่ระบุใน repository profile หลังเผยแพร่ควรเปิด GitHub Private Vulnerability Reporting และอัปเดตลิงก์ในไฟล์นี้

รายงานควรมี:

- ผลกระทบและผู้ใช้ที่เสี่ยง
- เวอร์ชัน/commit
- ขั้นตอนทำซ้ำขั้นต่ำ
- Python, Windows, FFmpeg/ffprobe versions
- ไฟล์หรือ metadata จำลองที่ไม่มีข้อมูลส่วนตัว
- การโจมตีต้องมี interaction/permission ใด
- แนวทางลดผลกระทบถ้ามี

อย่าส่ง token, cookie, private URL, copyrighted/private media หรือ path ที่ระบุตัวบุคคล

## Security boundaries

- Clipora ประมวลผล local media และไม่มี network/account/telemetry ในรุ่นปัจจุบัน
- Media เป็น untrusted parser input และถูกส่งให้ external FFmpeg
- ผู้ใช้รับผิดชอบติดตั้งและอัปเดต FFmpeg จากแหล่งเชื่อถือได้
- Clipora ไม่ออกแบบเพื่อข้าม DRM, paywall, login หรือ access control
- Source media ต้องไม่ถูกแก้ไขหรือลบ
- Output cleanup ต้องจำกัดเฉพาะไฟล์ที่ job สร้างและเป็นเจ้าของ
- Subprocess ต้องใช้ argument list และไม่ใช้ shell interpretation

## Response process

Maintainers ควร acknowledge รายงาน, ทำซ้ำใน environment ปลอดภัย, จำแนก severity/scope, สร้าง regression test ที่ไม่เผย exploit เกินจำเป็น, แก้ใน private branch และเผย security advisory/release เมื่อพร้อม

ไม่มี SLA อย่างเป็นทางการในช่วง pre-release แต่ควรยืนยันการรับรายงานโดยเร็วและแจ้งสถานะโดยไม่เปิดเผยรายละเอียดก่อนแก้ไข
