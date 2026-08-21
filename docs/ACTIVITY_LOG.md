# Clipora PC — Activity Log (บันทึกกิจกรรมและการพัฒนา)

ไฟล์นี้ใช้สำหรับบันทึกรายละเอียดการทำงาน การเปลี่ยนแปลง และสถานะของโปรเจกต์ Clipora PC ในทุกช่วงเวลา

---

## แผนงานการพัฒนา (Roadmap)
1. [x] สร้างระบบบันทึกกิจกรรม (`docs/ACTIVITY_LOG.md`)
2. [x] ระบบคิวงาน (Batch Processing)
3. [x] ระบบตัดช่วงเวลา (Media Trimming)
4. [x] ระบบตรวจสอบพื้นที่ดิสก์ว่างล่วงหน้า (Disk Space Check)
5. [x] ระบบตรวจสอบความสมบูรณ์ของไฟล์ต้นทาง (Source File Integrity Check)
6. [x] ระบบล้างแคชชั่วคราวตกค้าง (Orphaned Cache Cleanup)
7. [x] ปุ่มคัดลอก Error Log สะดวกๆ (`ErrorDialog` พร้อมปุ่ม Copy)
8. [x] ระบบแจ้งเตือนการอัปเดตแอปพลิเคชันหลัก (App Update Notification)
9. [x] ระบบจำกัดทรัพยากรการประมวลผล (CPU/Thread Limiter สำหรับ Demucs)

---

## ประวัติการทำงาน

### 2026-08-21
- เริ่มต้นจัดทำแผนงานพัฒนา 12 หัวข้อ (ยกเว้นเรื่องคุกกี้)
- สร้างไฟล์ `docs/ACTIVITY_LOG.md` เพื่อบันทึกประวัติการเปลี่ยนแปลงในไฟล์เดียว
- พัฒนาและเพิ่มฟีเจอร์สำคัญครบถ้วน:
  1. ระบบล้างแคชชั่วคราวตกค้าง (Orphaned Cache Cleanup)
  2. ปุ่มคัดลอก Error Log สะดวกๆ (`ErrorDialog`)
  3. ระบบตรวจสอบพื้นที่ดิสก์ว่างล่วงหน้า (Disk Space Check)
  4. ระบบตรวจสอบความสมบูรณ์ของไฟล์ต้นทาง (Source File Integrity Check)
  5. ระบบจำกัดทรัพยากรการประมวลผล (CPU/Thread Limiter สำหรับ Demucs)
  6. ระบบตัดช่วงเวลา (Media Trimming)
  7. ระบบคิวงาน (Batch Processing)
  8. ระบบแจ้งเตือนการอัปเดตแอปพลิเคชันหลัก (App Update Notification)
- รัน Unit/Integration Tests ผ่านทั้งหมด 163 tests ครบถ้วนสมบูรณ์
