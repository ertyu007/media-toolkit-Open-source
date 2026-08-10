# คู่มือ Code Signing สำหรับ Clipora

## ทำไมต้องลงนาม

Windows และโปรแกรมป้องกันไวรัสฟันธงไฟล์ที่ไม่รู้จักว่าเป็น "ความเสี่ยง" เพราะไม่มีลายเซ็นที่เชื่อถือได้:

- **SmartScreen** แสดง "ผู้เผยแพร่ที่ไม่รู้จัก" และขวางการเปิดก่อน
- **Antivirus บางตัว** flag โปรแกรมที่ build ด้วย PyInstaller ว่าเป็น false positive เพราะแพ็กเกจไม่มี metadata ครบและไม่มีลายเซ็น

การลงนาม Authenticode (SHA-256 + RFC 3161 timestamp) ด้วย certificate ที่ CA รู้จักช่วยลดทั้งสองอย่างได้มาก และถ้าลงนามทุกไฟล์ EXE ของตัวแอปและตัวติดตั้งด้วย certificate ตัวเดียวกัน Windows จะแสดง "ผู้เผยแพร่: Clipora Contributors" อย่างถูกต้อง

## สิ่งที่ build ทำอยู่แล้วเพื่อลด false positive

- ใช้ PyInstaller แบบ onedir (ไม่ใช่ onefile) — onefile มักถูก flag บ่อยกว่า
- ปิด UPX compression (`upx=False`)
- ฝัง version resource ครบ (CompanyName, ProductName, Copyright, ฯลฯ)
- ฝัง application manifest มาตรฐาน: `asInvoker`, DPI-aware, `longPathAware`, รองรับ Windows 10/11 (`packaging/clipora.manifest`)
- ตัวติดตั้ง Inno Setup มี metadata ครบ (VersionInfo*, UninstallDisplayName, AppCopyright, SetupLogging)

แต่ทั้งหมดนี้ยังไม่ทดแทนการลงนามจริง ตัวติดตั้งที่ไม่ได้ sign ยังแสดงคำเตือน SmartScreen เสมอ

## วิธีที่ 1: ลงนามด้วย .pfx certificate

1. ซื้อ OV/EV code-signing certificate จาก CA (DigiCert, Sectigo, SSL.com ฯลฯ) หรือขอแบบฟรีสำหรับ open-source เช่น [SignPath](https://signpath.io/) และ [Azure Trusted Signing](https://learn.microsoft.com/azure/trusted-signing/)
2. นำเข้า certificate พร้อม private key แล้ว export เป็น `.pfx` (พร้อม password)
3. ตั้งค่า environment variable ก่อนรัน `build_windows.ps1`:

   ```powershell
   $env:CLIPORA_CERT_PATH = 'C:\secure\clipora.pfx'
   $env:CLIPORA_CERT_PASSWORD = 'password'
   $env:CLIPORA_SIGNTOOL = 'C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe'   # ไม่บังคับ
   .\scripts\build_windows.ps1
   ```

   build จะลงนาม `Clipora.exe` และตัวติดตั้งให้อัตโนมัติ ถ้าไม่ตั้งค่า build จะข้ามการลงนาม (ยังได้ installer เหมือนเดิม)

## วิธีที่ 2: ลงนามด้วย Azure Trusted Signing

Azure Trusted Signing ของ Microsoft เหมาะกับ CI/open-source มากเพราะ certificate อยู่ใน cloud ไม่ต้องเก็บ .pfx

1. สร้าง Azure Trusted Signing account + certificate profile ในพอร์ทัล Azure ตาม [Microsoft docs](https://learn.microsoft.com/azure/trusted-signing/)
2. ตั้งค่า environment variable ในเครื่อง หรือ secrets ใน GitHub:

   | Variable / Secret | ใช้เป็น |
   |---|---|
   | `CLIPORA_AZURE_ACCOUNT_URI` | endpoint URI ของ account |
   | `CLIPORA_AZURE_CLIENT_ID` | application (client) id |
   | `CLIPORA_AZURE_CLIENT_SECRET` | client secret |
   | `CLIPORA_AZURE_TENANT` | tenant id |
   | `CLIPORA_AZURE_CERT_PROFILE` | ชื่อ certificate profile |
   | `CLIPORA_AZURE_CERT_NAME` | ชื่อ certificate (ถ้าต้องการ) |

   > ต้องการ signtool จาก Windows SDK 10.0.22621+ หรือรุ่นที่รองรับ Azure Trusted Signing ตรวจด้วย `signtool /?` ว่ามีตัวเลือก `/kvu`

## ตั้งค่าใน GitHub Actions

สร้าง secrets ตามที่ `release.yml` อ่าน (เลือกแบบใดแบบหนึ่ง):

**แบบ .pfx:** เอาไฟล์ .pfx มา base64:
```powershell
[Convert]::ToBase64String([IO.File]::ReadAllBytes('C:\secure\clipora.pfx'))
```
- `CLIPORA_CERT_BASE64` — base64 ของ .pfx
- `CLIPORA_CERT_PASSWORD` — password

**แบบ Azure Trusted Signing:** ตั้ง secrets `CLIPORA_AZURE_*` ตามตารางด้านบน

Workflow ลงนาม `Clipora.exe` และตัวติดตั้งให้อัตโนมัติ และ**จะไม่ fail** ถ้ายังไม่ได้ตั้ง secrets (ลงนามแบบไม่มี cert ได้ตามปกติ)

## ตรวจสอบผลลัพธ์

หลัง build ตรวจด้วย PowerShell:

```powershell
Get-AuthenticodeSignature -FilePath 'dist\Clipora\Clipora.exe'
Get-AuthenticodeSignature -FilePath 'dist\installer\Clipora-Setup-0.4.1-x64.exe'
```

ต้องการเห็น `Status = Valid` และ `SignerCertificate` เชื่อมกับ root ที่ Windows รู้จัก ถ้าเป็น self-signed หรือ certificate ที่ยังไม่ trust จะยังเห็นคำเตือน

## ถ้ายังถูก flag ว่าไวรัส

- ยืนยันว่า signature `Valid` และ timestamp ไม่หมดอายุ (RFC 3161)
- ส่งตัวอย่างไปยัง vendor ที่ flag เช่น [Microsoft Security Intelligence](https://www.microsoft.com/en-us/wdsi/filesubmission), Malwarebytes, ESET, Kaspersky ฯลฯ โดยระบุว่าเป็นโปรแกรม open-source (แนบลิงก์ repo และ hash)
- ใช้ certificate เดียวกันทุกครั้งเพื่อสร้าง reputation
- ถ้ายัง flag หลังลงนามครบ แสดงว่าผู้ใช้ต้อง update signature database ของ AV ตัวเอง
