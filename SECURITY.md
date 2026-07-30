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

- Clipora ไม่มี account หรือ telemetry ไฟล์ที่ผู้ใช้เลือกจากเครื่องไม่ถูกอัปโหลด
- โหมด URL เชื่อมต่อเว็บไซต์ต้นทางผ่าน yt-dlp และบันทึกลงเครื่องเท่านั้น
- URL import ไม่รองรับ credential, cookie, private media, paywall หรือ DRM
- Media เป็น untrusted parser input และถูกส่งให้ external FFmpeg
- URL และข้อมูลตอบกลับจากเว็บไซต์เป็น untrusted input เช่นกัน
- Windows Setup Assistant ดาวน์โหลด FFmpeg/yt-dlp/Deno เฉพาะ immutable HTTPS URLs ที่ระบุใน source บังคับขนาดสูงสุด ตรวจ SHA-256 และ stage ทุกไฟล์ก่อน atomic replacement
- การอัปเดต dependency manifest ต้องตรวจ release/source/license ใหม่ ห้ามใช้ `latest` URL หรือข้าม checksum และต้องทดสอบ checksum mismatch/cancellation
- ผู้ใช้ source อาจใช้เครื่องมือจาก PATH หรือ explicit `CLIPORA_*` override และรับผิดชอบความน่าเชื่อถือของ binary นั้น
- Clipora ไม่ออกแบบเพื่อข้าม DRM, paywall, login หรือ access control
- Source media ต้องไม่ถูกแก้ไขหรือลบ
- Output cleanup ต้องจำกัดเฉพาะไฟล์ที่ job สร้างและเป็นเจ้าของ
- URL temp cleanup ต้องจำกัดเฉพาะ directory ที่มี marker ของงานและอยู่ใต้ destination
- Subprocess ต้องใช้ argument list และไม่ใช้ shell interpretation
- Setup archive extraction ต้องเลือกเฉพาะ allowlisted member ที่ match เพียงหนึ่งไฟล์ ห้าม `extractall` กับ archive จาก network

## Response process

Maintainers ควร acknowledge รายงาน, ทำซ้ำใน environment ปลอดภัย, จำแนก severity/scope, สร้าง regression test ที่ไม่เผย exploit เกินจำเป็น, แก้ใน private branch และเผย security advisory/release เมื่อพร้อม

ไม่มี SLA อย่างเป็นทางการในช่วง pre-release แต่ควรยืนยันการรับรายงานโดยเร็วและแจ้งสถานะโดยไม่เปิดเผยรายละเอียดก่อนแก้ไข
