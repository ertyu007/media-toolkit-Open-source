# บันทึกงาน (Work Notes) — ฟีเจอร์แยกสเต็มเสียง (Stem Separation) + อัปเดต yt-dlp

อัปเดตล่าสุด: 2026-09-28

## ทำวันนี้ (2026-09-28) — toast มินิมอล (ยังไม่ bump version)

- **ตามวง**: ถอดวงไอคอน + ปุ่ม ✕ ออก เหลือแถบสี+ข้อความ กดตรงไหนก็ปิด (หมดเวลาแล้วหายเองเหมือนเดิม)
- **เหลี่ยม**: เลิก fade `-alpha` (สงสัยตีกับ `-transparentcolor` จนมุมไม่โปร่งใส) เหลือสไลด์อย่างเดียว
- **Tests**: full suite ผ่าน; smoke สร้าง/ปิดผ่าน

## ทำวันนี้ (2026-09-28) — yt-dlp เลิกโหลดเอง (ยังไม่ bump version)

- **สาเหตุที่โหลดเอง**: เช็คอัตโนมัติตอนเปิดแอปเจอเวอร์ชันใหม่แล้วเรียก `_start_ytdlp_update` ทันทีโดยไม่ถาม → เปลี่ยนเป็น toast แจ้ง + ให้กด Ctrl+U เอง (กดมือยังถามยืนยันเหมือนเดิม)
- **Tests**: full suite รอรอบนี้ (ไม่มีเทสคุม path นี้); `USER_GUIDE` §7 sync ตามจริง

- **วงกลมขอบๆ**: ตัว `ⓘ` พึ่งฟอนต์ fallback บางเครื่องวาดเป็นกล่อง → เลิกใช้ glyph ผสม เปลี่ยนทุก type เป็นวงแหวนวาดเอง + ตัวอักษร `i/✓/!/✕` (มีใน Segoe UI แน่นอน)
- **Tests**: full suite ผ่าน (toast ต้องจอจริง — smoke 4 type เปิด/ปิดผ่าน)

- **dropdown มน**: ถอด `ttk.Combobox` ออกจาก `RoundedCombobox` เขียน popup เอง (toplevel มน r=12 ผ่าน `-transparentcolor` + แถวไฮไลต์มน r=8) — ไม่มีขอบเหลี่ยมดั้งเดิมเหลือ; API เดิมครบ (`textvariable/values/state/values=/focus_set/<<ComboboxSelected>>`) + คีย์บอร์ด (เปิด/ลูกศร/Enter/Esc) + flip ขึ้นบนถ้าจอล่างไม่พอ; ลบ style `Pill.TCombobox` + `option_add` ที่ตายตาม
- **toast ในภาพคือของเก่า**: โค้ดปัจจุบันเป็น canvas มนแล้ว (smoke นับ 15 items) — ผู้ใช้รัน build เก่าอยู่
- **Tests**: full suite รอรอบนี้ (popup ต้องจอจริง — smoke เปิด/เลือก/ปิดผ่าน); `USER_GUIDE` ไม่ต้องแก้ (พฤติกรรมผู้ใช้เหมือนเดิม)

## ทำวันนี้ (2026-09-28) — โหมดแยกปุ่มมีล็อกสเต็ม (ยังไม่ bump version)

- **แยกปุ่ม+ล็อก**: `SegmentedControl` รับ `gap` (ปุ่มแยกเป็นลูกๆ แต่ pill เลือกยังสไลด์ข้ามทั้งแถวเหมือนเดิม) + `locked`/`on_locked` (ติ๊ก 🔒 เทา กดแล้วไม่เปลี่ยนโหมด); hero ใช้ `gap=8` ล็อก `stems` จนกว่า `separator_installed()` กดตอนล็อกพาไปติดตั้งชุดแยกสเต็ม; รีเฟรชล็อกใน `_sync_options` + `_tools_ready`
- **Tests**: `test_segmented.py` ใหม่ (math ล้วน ไม่ต้องจอ: layout/hit/edge); `USER_GUIDE` §3 sync ตามจริง

- **เอาออกเหมือนกัน**: ถอดปุ่ม 🗑 ท้ายแถวโหมดปกติด้วย (ถังขยะถอดไปก่อนแล้ว) ลบทุกอย่างผ่านคลิกขวาอย่างเดียว + ลบคอลัมน์ actions/`_history_header` ที่ตายตาม
- **Tests**: full suite รอรอบนี้; `USER_GUIDE` §9 sync ตามจริง

- **crash ตั้งค่า**: โค้ด footer ปุ่มยกเลิก/บันทึกหลุดเข้าไปใน `_uninstall` (edit ผิดจุด) กดถอนติดตั้งเลย `NameError` → ย้ายกลับ `__init__` + smoke เปิด dialog ยืนยัน
- **ถังขยะไร้ปุ่ม**: ถอดปุ่มกู้คืน/ลบถาวรท้ายแถว ทำผ่านคลิกขวาอย่างเดียว (เมนูมีครบอยู่แล้ว) + ยุบคอลัมน์ actions ในโหมดถังขยะให้แถวเต็มความกว้าง; กัน `_select_row` ตอน actions เป็น None
- **Tests**: full suite รอรอบนี้; `USER_GUIDE` §9 sync ตามจริง

## ทำวันนี้ (2026-09-28) — แก้เสียงแจ้งเตือนเพี้ยน (ยังไม่ bump version)

- **สาเหตุ**: ตารางโน้ตป้าย `C#6/E6` แต่ความถี่จริงคือ D6/G6 (1174/1568Hz แหลมแสบหู) → แก้เป็น A-major แท้ `880/1109/1319Hz` + เว้น gap 25ms ไม่ให้เสียงเละ
- **ลองฟัง**: ตั้งค่าแถวเสียงมีปุ่ม `ลองฟัง` กดเช็กเสียงได้เลย
- **Tests**: `test_sound.py` ใหม่ (โน้ตตรง major arpeggio ตามสูตร tempered, รวม <600ms, ยิงแล้วไม่พัง)

- **popup ตามวง**: ป้ายธีมเหลือ `ธีม`, แถวโฟลเดอร์เต็มความกว้าง (ช่อง `RoundedEntry` ขยาย ปุ่ม `เลือก…`/`ถอนการติดตั้ง…` กระชับ), เกี่ยวกับมีคำอธิบาย 2 บรรทัดไม่โล่ง, หน้าต่างกว้าง 600
- **ยืนยัน+ถอนหมดจด**: confirm บอกหมด (ลบโปรแกรม+เครื่องมือ+ตั้งค่า/ประวัติ ไฟล์งานไม่โดน); `clipora.iss` เพิ่ม `[UninstallDelete]` ลบ `%LOCALAPPDATA%\Clipora` ทั้งยวง
- **toast มน**: `ToastManager` วาดการ์ดมน (r=14) บน canvas + `-transparentcolor` (fallback เหลี่ยมถ้า platform ปฏิเสธ), ข้อความ/ปิดเหมือนเดิม
- **Tests**: full suite รอรอบนี้ (toast/iss ต้องจอ+ติดตั้งจริง — smoke สร้าง toast + `test_packaging` คุม iss); `USER_GUIDE` §3 sync ตามจริง

- **dropdown เหลี่ยม**: ขอบขาวคือ border ดั้งเดิมของ popup listbox → `option_add` ปิด (`borderWidth/highlightThickness/activeBorderWidth 0` + `relief flat`) เหลือแต่พื้นเข้มตามธีม (เหลี่ยมมนวาดไม่ได้ด้วย Tk ดั้งเดิม — ไร้ขอบแล้วกลืนพอ)
- **ถอนการติดตั้ง**: เกี่ยวกับใน popup เพิ่มปุ่ม `ถอนการติดตั้ง…` → `_uninstall_app`: รุ่นติดตั้ง (frozen) หา `unins000.exe` ข้าง exe ถามยืนยันแล้วรัน (arg list) + ปิดแอป, หาไม่เจอ/รันซอร์สโค้ดเปิดหน้า Apps settings (มี fallback) — กันกดตอนมีงานรัน; helper บริสุทธิ์ `find_clipora_uninstaller` + เทส 2
- **Tests**: full suite รอรอบนี้; `USER_GUIDE` §3 sync ตามจริง

- **popup ตามวง**: ป้ายธีมยาวตัดเหลือ `ธีม` (+โน้ตเปิดแอปใหม่ถึงมีผล), แถวโฟลเดอร์บันทึกย้ายเต็มความกว้าง (label บน ช่อง+ปุ่มล่าง) หมดปัญหาพาธขาด, หน้าต่างกว้าง 600
- **กระชับคำทั้งโปรแกรม**: วางลิงก์/เลือกไฟล์หรือลากมาวาง/เปิดโฟลเดอร์/คู่มือ/ตรวจอัปเดต/เสียงแจ้งเตือน/ค่าเริ่มต้นงาน/ยินยอมติดตั้งเครื่องมือ/คำอธิบายโหมด/trim/Toast ธีม (เลี่ยงข้อความที่เทส pin ไว้ทั้งหมด)
- **debug เฉพาะ encode**: ตัด log นอกงานแปลง (พรีวิว/ประวัติ/ถังขยะ/ลากวาง/ตั้งค่า/ตรวจอัปเดต/สถานะเครื่องมือ) เหลือพารามิเตอร์งาน/เปลี่ยนเฟส/speed ทุก 5วิ/ผลรวม/ล้มเหลว/ยกเลิก; ถอด `on_log` ที่ตายตาม
- **Tests**: full suite รอรอบนี้; `USER_GUIDE` §3 sync ตามจริง

- **ตัดซ้ำตามฟีดแบ็ก**: ถอดปุ่ม `ตรวจหาการอัปเดต` ใน popup (มีใน sidebar แล้ว), ถอด `auto_debug` ทั้งยวง (setting/var/hook/dialog เทสอัปเดตตาม, ค่าเก่าในไฟล์ถูกล้างตอนบันทึก)
- **debug เปิดค้าง**: ถอดปุ่มกาง/พับ + `_debug_visible` กล่อง 6 บรรทัดอยู่ถาวร; เนื้อละเอียดขึ้น — พารามิเตอร์งานเต็ม (`โหมด/แหล่ง/ต้นฉบับ/ปลายทาง/รูปแบบ/คุณภาพ/fps/สเต็ม`), ผลรวมขนาด, ชื่อไฟล์ทุกประวัติ, พรีวิว (ชื่อ/ช่อง/เวลา), ลากวาง, บันทึกตั้งค่า, ประวัติถังขยะทุกแอ็กชัน, สถานะเครื่องมือทีละตัว, ผลตรวจอัปเดต; ตัดซ้ำ (`_done`/`_done_stems` เหลือ phase+ผลรวม+ชื่อประวัติ)
- **Tests**: full suite รอรอบนี้; `USER_GUIDE` §3 sync ตามจริง

## ทำวันนี้ (2026-09-28) — หน้าต่างเครื่องมือมีสถานะ + dropdown ไม่ขาวแล้ว (ยังไม่ bump version)

- **พื้นขาว dropdown**: ตัวจริงคือ parent map ของ clam บังคับ `readonly → #dcdad5` ทับ `configure` (บทเรียน: style map สืบทอด+รวมกัน configure อย่างเดียวไม่ชนะ state) → เติม `fieldbackground` ทุก state + `selectbackground/selectforeground` ใน map; lookup ยืนยันทุก state ได้ `#232329`/ม่วงแล้ว
- **เครื่องมือหายแปลก**: โหมดซ่อมเคยเปิด wizard ต้อนรับเต็มยศ+ติดตั้งทับทั้งหมด → เปลี่ยนเป็น 4 ขั้น (สถานะ/ตรวจสอบ/ติดตั้ง/เสร็จสิ้น) หน้าแรกรัน `check_tool/check_ytdlp/check_javascript_runtime` (reuse `scripts/check_environment`, ไม่ freeze เพราะ worker thread) + `separator_installed` โชว์ ✓/✕ ทีละตัวพร้อมเวอร์ชัน; ปุ่ม `ติดตั้งส่วนที่ขาด (N)` ติดตั้งเฉพาะที่หาย (`force=False`) ครบแล้วปุ่มกลายเป็นปิด; ลบ `WIZARD_STEPS`/import ตาย; first-run/separator flow เดิมไม่แตะ
- **Tests**: full suite รอรอบนี้ (status page ต้องมีจอ+เครื่องมือจริง เลย smoke ด้วย mainloop แทน); `USER_GUIDE` §2 sync ตามจริง

- **debug การทำงาน**: แถบล่างเพิ่มปุ่ม `▸ debug การทำงาน` กาง `tk.Text` 6 บรรทัด (พับอยู่ดีฟอลต์ ปุ่มเริ่มเลยลอยสูงขึ้น) บันทึก `[เวลา] ข้อความ` ตอนเริ่มงาน/เปลี่ยนเฟส/ความเร็วดาวน์โหลด (ทุก 5วิ)/เสร็จ/ล้มเหลว/ยกเลิก/พรีวิว; ตัดเหลือ 300 บรรทัด; `_debug` เรียกเฉพาะ main thread เท่านั้น
- **crash ลากไฟล์ (critical)**: `widget.after` ใน `WndProc` ทำ interpreter พัง (bisect ยืนยัน) → proc ใหม่แตะแค่ Win32 + queue ส่วน poller (`after` ปกติบน main thread) ค่อยยิง callback; proof ด้วย HDROP จำลองยิง `WM_DROPFILES` จริง end-to-end ผ่าน; เติม argtypes `DragQueryFileW`/`DragFinish` ที่ทำให้ drop จริงรอบแรกพัง
- **Tests**: `test_ui_helpers` +1 (`format_debug_line`); `USER_GUIDE` §3 sync ตามจริง

## ทำวันนี้ (2026-09-28) — ลากไฟล์วางจาก Explorer (ยังไม่ bump version)

- **ไม่เพิ่ม dependency**: Tk รับ `WM_DROPFILES` ไม่ได้ → `clipora/dragdrop.py` ใหม่ ใช้ ctypes ล้วน (`DragAcceptFiles` + subclass `WndProc`, คืน proc เดิมตอน destroy) callback กลับ main thread ผ่าน `after`
- **วางแล้วฉลาด**: ไฟล์→ช่องแหล่งสื่อ (อยู่โหมด URL สลับเป็นโหมดไฟล์ให้เอง) โฟลเดอร์→ช่องบันทึกที่ เลือกไฟล์แรกถ้าลากมาหลายอัน ไม่รับตอนมีงานรันอยู่; hint ใต้ช่องไฟล์บอกว่าลากวางได้
- **Tests**: `test_ui_helpers` +4 (`route_dropped_paths` ล้วน, ctypes ทดสอบ headless ไม่ได้); `USER_GUIDE` §3 sync ตามจริง

## ทำวันนี้ (2026-09-28) — ปุ่ม ☰/« ตัวเดียว + ตั้งค่าท้าย sidebar (ยังไม่ bump version)

- **ปุ่มเดียวสลับกัน**: ปุ่มบน topbar แสดง « ตอนแถบเปิด (กด=ซ่อน) / ☰ ตอนแถบปิด (กด=เปิด) ผ่าน `_sync_sidebar_toggle`; ถอดปุ่ม « ซ่อน ท้ายแถบออกประหยัดที่
- **ตั้งค่าท้ายแถบ** (จำลง `settings.json`, เขียนแบบไม่พังงาน): 📁 **โฟลเดอร์บันทึก** (เรียก `_choose_destination` ตัวเดียวกับฟอร์มหลัก), สวิตช์**เสียงแจ้งเตือน** (`chime_enabled` ตัด `play_completion_chime` ใน `_show_result`), สวิตช์**ตรวจอัปเดตอัตโนมัติ** (`auto_update_check` ตัด startup check yt-dlp+app — กดตรวจมือยังได้เสมอ)
- **Tests**: full suite รอรอบนี้; `USER_GUIDE` §3 sync ตามจริง

## ทำวันนี้ (2026-09-28) — ประวัติคอลัมน์ Explorer + จำรายการที่เลือก (ยังไม่ bump version)

- **ปุ่มถังขยะแยกขวาสุด**: กลุ่ม filter เหลือ 4 pill (ทั้งหมด/เพลง/วิดีโอ/สเต็ม) ปุ่มถังขยะแยกเป็นปุ่มเดี่ยวขวามือ กดสลับโหมดถังขยะ/ทั้งหมด (`_toggle_trash_filter`) ติดไฮไลต์ `SideActive` ตอนอยู่ในถังขยะ (`_sync_trash_button` ท้าย `_render`)

- **คอลัมน์แบบ Explorer**: header คงที่ **ชื่อ/ประเภท/วันที่/ขนาด** + แถว grid คอลัมน์กว้างพิกเซลคงที่ (`_HISTORY_COLUMN_MINSIZES`) header ตรงกับแถวเสมอ; ขนาดอ่านจากไฟล์จริง ไฟล์หายขึ้น `—` แถวเป็นสีจาง; ชื่อยาวตัด 40 ตัวอักษร (ซ่อม `rowconfigure` ผิดแถวที่ทำลิสต์ไม่ยืดด้วย)
- **จำ path ที่เลือก**: คลิกแถวไหนจำ `id` ลง `settings.json` (`selected_history_id`, เขียนแบบไม่พังงาน) เปลี่ยนฟิลเตอร์/สลับ view/เปิดแอปใหม่ยังเลือกที่เดิม (`find_history_index` มี fallback เทียบ target path); ลบรายการที่จำไว้ล้างค่าทิ้ง
- **Tests**: `test_ui_helpers` +3 (หา id เจอ/fallback target/ไม่เจอได้ None); full suite รอรอบนี้; `USER_GUIDE` §9 sync ตามจริง

## ทำวันนี้ (2026-09-28) — ประวัติมีถังขยะ 30 วัน + เมนูคลิกขวา (ยังไม่ bump version)

- **ช่องโหว่ลบแล้วหายเลย**: ปุ่ม 🗑 เดิมลบถาวรทันที → ถามยืนยันก่อนทุกครั้ง แล้วย้ายไปถังขยะ (`trashed_at`) แทน; ของในถังขยะถูก purge อัตโนมัติตอนโหลดเมื่อเกิน 30 วัน (`TRASH_RETENTION_SECONDS`); ไฟล์จริงไม่ถูกแตะทุกกรณี
- **ถังขยะมองเห็นได้**: pill เพิ่ม **ถังขยะ** แถวในนั้นมีปุ่ม **กู้คืน** + **ลบถาวร** (ถามยืนยัน); `history.py` เพิ่ม `trash_entry`/`restore_entry`/`trash_all`/`empty_trash`/`load_trash` (ฟิลด์ใหม่มี default ไฟล์เก่าอ่านได้); เติมบั๊กแฝง `add_entry` ที่เคยเขียนทับถังขยะทิ้ง (ใช้ `_read_all` แทน `load_history`)
- **ปุ่มล่างหายไป**: **เปิดตำแหน่งไฟล์**/**ลบทั้งหมด** ถูกถอด → คลิกขวาที่ว่าง/ที่แถวเปิด `tk.Menu` (เปิดตำแหน่งไฟล์/ลบรายการนี้/ลบทั้งหมด…/ล้างถังขยะ…, ปิดเองเมื่อคลิกที่อื่นแบบ Windows, โทนเดียวกับเมนู history ของ destination)
- **Tests**: `test_history` +5 (ซ่อน/กู้คืน/purge เกินอายุ/trash_all+empty/new ไม่ทับถังขยะ); `USER_GUIDE` §9 sync ตามจริง

## ทำวันนี้ (2026-09-28) — skeleton shimmer + ปกอัตราส่วนจริง (ยังไม่ bump version)

- **shimmer แทน pulse**: placeholder เดิมเป็นข้อความกระพริบ → วาดบน Canvas ตรงเลย์เอาต์จริง (กล่องรูปซ้าย + แถบข้อความขวา 2 แถบ) มีแถบแสงกวาดซ้าย→ขวาทุก 50ms (`_tick_skeleton_shimmer`, สี `SECONDARY_BORDER` บนพื้น `FIELD`); วาดตามความกว้างจริงผ่าน `<Configure>`, หยุด loop ตอนข้อมูลมา/ซ่อน/พิมพ์ใหม่ (`_stop_preview_anim`)
- **เลย์เอาต์ล็อก**: แยก `_preview_body` (รูปซ้าย ข้อความขวา) ออกจาก `_skel` สลับ show/hide ไม่กระโดด; ปก `fit_photo_image(…, 168, 120)` คงอัตราส่วนจริงไม่ครอป (แนวตั้งโชว์สูงเต็ม ไม่โดนบีบเป็น 16:9)
- **Tests**: full suite รอรอบนี้ (animation ทดสอบ headless ไม่ได้ — logic บริสุทธิ์ไม่มีเพิ่ม); `USER_GUIDE` §4 sync ตามจริง

## ทำวันนี้ (2026-09-28) — ประวัติเหลือปุ่มถังขยะรายแถว (ยังไม่ bump version)

- **ลดความซับซ้อนตามฟีดแบ็ก**: checkbox + เลือกทั้งหมด + ตัวนับ + ลบที่เลือก → แถวละปุ่ม 🗑 ลบทันที (ไม่ถาม, ไม่โดนไฟล์จริง) + คง **ลบทั้งหมด** (ถามยืนยัน) ไว้ขวาสุด; คลิกแถวเลือก (ไฮไลต์) ดับเบิลคลิก/ปุ่มเปิดตำแหน่งไฟล์เหมือนเดิม ชื่อยาวตัด 55 ตัวอักษร
- **Tests**: full suite รอรอบนี้; `USER_GUIDE` §9 sync ตามจริง

## ทำวันนี้ (2026-09-28) — พรีวิว skeleton + ขนาดไฟล์ + speed/ETA (ยังไม่ bump version)

- **skeleton**: การ์ดพรีวิวลิงก์โชว์ placeholder ทันทีที่ URL ถูกต้อง (`_show_preview_skeleton` + pulse สลับสี 450ms) แทนที่จะว่างจน worker ตอบ; หยุด pulse ตอนข้อมูลมาจริง/ซ่อน/ยกเลิก (กัน loop ซ้อนด้วย `_stop_preview_pulse`)
- **ข้อมูลดีขึ้น**: `preview.py` ขอเพิ่ม `duration` (วินาที), `filesize_approx`, `filesize` จาก yt-dlp; UI โชว์ `ช่อง • ระยะเวลา • ≈ขนาด` — ไม่มีขนาดจริง + โหมดเสียง = ประมาณจากความยาว (192kbps) ติดป้าย "(ประมาณ)"
- **speed/ETA ตอนโหลด**: progress template เพิ่ม `|speed|ETA`, parser ใหม่ `parse_import_progress_detail` (ตัวเก่า `parse_import_progress` ยังคืน float เหมือนเดิม, รองรับบรรทัดเก่าไม่มี `|`), `on_detail` optional ไหลผ่าน `_run_import_process`/`_run_import_with_fallback`/`import_url`/`import_audio_for_processing` (default None ไม่แตก caller เก่า); UI ต่อ `% • speed • เหลือ ETA` ทั้งงาน URL ตรงและ stems-URL
- **Tests**: `test_preview` +4 (7 ฟิลด์, fallback exact, NA, estimate), `test_importer` +3 (speed/ETA, NA, legacy); `USER_GUIDE` §4 sync ตามจริง

## ทำวันนี้ (2026-09-28) — สเต็มเดี่ยวไม่ zip + ประวัติ + พรีวิวลิงก์ (ยังไม่ bump version)

- **สเต็มเดี่ยวไม่ zip**: `separate_audio` เลือกสเต็มเดียวคืนไฟล์เสียงเปล่า (`เพลง_vocals.mp3`) เลือกหลายสเต็มค่อย zip; helper บริสุทธิ์ใหม่ `separate_expected_outputs()` ให้ UI เช็ก overwrite + เทสต์ได้โดยไม่รัน demucs; อัปเดต integration test ที่เคย assume zip; `USER_GUIDE` §6/§9 แก้ตามจริง (ของเดิมอ้างว่าไฟล์แยกยังอยู่ด้วย — ไม่จริง มันอยู่ใน workspace ชั่วคราวที่ถูกล้าง)
- **ประวัติ** (`clipora/history.py` ใหม่ + `tests/test_history.py` 8 tests): JSON capped 200 ต่อท้าย settings บันทึกทุกงานสำเร็จใน `_show_result` จุดเดียว (ไม่พังงานถ้าเขียนไม่ได้); dialog ใน `ui.py` (เปิดจาก ☰) มีกรอง pill ทั้งหมด/เพลง/วิดีโอ/สเต็ม, เปิดตำแหน่งไฟล์, ลบทีละอัน/ลบทั้งหมด (ถามยืนยัน, ไม่ลบไฟล์จริง), แต้ม (ไฟล์หาย)
- **พรีวิวลิงก์** (`clipora/preview.py` ใหม่ + `tests/test_preview.py` 7 tests): `yt-dlp --skip-download --print` ดึง title/uploader/duration/thumbnail, โหลดปก (cap 5MB) แปลงเป็น PNG ผ่าน FFmpeg ในเครื่อง (ไม่เพิ่ม dependency, stdlib PhotoImage อ่านได้); UI debounce 1.2วิ + generation กันงานซ้อน, พังเงียบ (ไม่มีการ์ด ไม่ใช่ error), การ์ดค้างโชว์ตอนโหลดต่อ
- **Tests**: full suite รอรอบสุดท้าย

## ทำวันนี้ (2026-09-28) — sidebar แทน popup ประวัติ (ยังไม่ bump version)

- **sidebar ซ้ายพับได้**: ปุ่ม ☰ บน topbar + « ซ่อน ท้ายแถบ; มีมุมมองงาน/ประวัติ + แอ็กชันเครื่องมือ/อัปเดต yt-dlp/อัปเดตแอป/สนับสนุน/คู่มือ/รายงานปัญหา — ลบ `tk.Menu` ☰ ทั้งยวง
- **ประวัติฝังในหน้าหลัก**: `HistoryDialog` → `HistoryPanel` สลับ view กับฟอร์มงาน (footer ค้าง); `_open_history` → `_show_view('history')`; ลบ import `MENU_ACTIVE_BG` ที่ตาย
- **Tests**: full suite 231 ผ่าน + smoke sidebar (พับ/กาง/สลับ view/กรอง) ผ่าน; `USER_GUIDE` §3/§7/§9 sync ตามจริง

## ทำวันนี้ (2026-09-28) — ลบ DMCA + pill widgets + toast มุมขวาล่าง + เสียงเสร็จงาน (ยังไม่ bump version)

- **ลบ DMCA report**: ฟอร์มแค่เปิด mailto ไป gmail ส่วนตัว ไม่มี backend/blocklist จริง (grep ทั้ง repo แล้ว) ส่งแล้วเงียบ → ลบ `DmcaDialog` + เมนู + `build_dmca_mailto`/`DMCA_EMAIL`/`DMCA_NOTE` เก็บคำเตือนลิขสิทธิ์ไว้ครบ; อัปเดต `test_legal.py` + `USER_GUIDE` §ความปลอดภัยแล้ว
- **pill widgets** (`widgets.py`, ไม่เพิ่ม dependency): `SegmentedControl` วาดบน Canvas (รางมน + pill เลื่อน 140ms, ลูกศรซ้าย/ขวาได้), `RoundedEntry`/`RoundedButton` ทรง stadium, `Switch` แทน Checkbutton; ต่อเข้า `ui.py` เฉพาะฟอร์มหลัก (ปุ่มเริ่มงานยักษ์ + combobox ยังเดิม)
- **Ctrl+V ใน dialog**: `_on_paste_shortcut` เดิมดัก paste ทั้งแอป (ฟอร์ม DMCA วางไม่ได้) → คืน native paste ให้ทุก Entry/Text เก็บ hijack ไว้เฉพาะโฟกัสบนพื้นหลัง
- **toast**: ย้ายจากเหนือจอบน (ยึดปุ่ม ☰) ลงมุมขวาล่าง + ขยาย (10 bold, แถบ 5px)
- **เสียงเสร็จงาน**: `clipora/sound.py` ใหม่ (arpeggio A5→C#6→E6 ผ่าน winsound บน daemon thread) ต่อใน `_show_result` จุดเดียว
- **Security (importer)**: `validate_url` ถอดรหัส IP แฝง (hex/decimal/octal/shorthand) + fallback `08/09` เป็น decimal; `dialogs.sanitize_error_message` แดง path โลคัล + ตัด 1500 ตัวอักษร โดยไม่กิน `https://` (lookbehind)
- **รีวิวรอบสองจับบั๊กได้ 4 ตัว**: shell มนไม่ redraw ตอน resize, regex กิน URL, octal `08` bypass, history popup หลุดบน padding — แก้ + smoke ยืนยันแล้ว
- **เคลียร์ซาก sidebar/rail**: โค้ดถอด rail ไปแล้วแต่เหลือ style `Rail.*`, `_switch_view`/`_sync_rail`, dict ว่าง และ USER_GUIDE ยังอ้างรางซ้าย — ลบทิ้ง + sync คู่มือให้ตรงจริง (pill โหมด, สวิตช์สิทธิ์, เมนู ☰ อย่างเดียว)
- **Tests**: full suite **213 ผ่าน** (ลด 3 เทสต์ mailto ที่ลบไป, skipped 2 = network)

## ทำวันนี้ (2026-09-24) — Dev-Tool Edition: reskin + sidebar (ยังไม่ bump version)

- **เฟส 1 reskin** (`theme.py`): charcoal กลาง (`BG #121214`, panel `#1a1a1f`, field `#232329`), เส้นขอบคม 1px `#2e2e35`, ตัวหนังสือ `#e9e9ec`/`#9b9ba4`, ม่วงเหลือจุดเดียว (ปุ่มเริ่ม/active/progress/focus), motion จูนกระชับ (100–200ms)
- **เฟส 2 sidebar**: รางซ้าย 4 รายการ (ไฟล์ในเครื่อง/ดาวน์โหลด/แยกสเต็ม/เครื่องมือ) + เส้นคั่น, `_switch_view()` preset kind/mode แล้วเรียก sync เดิม, `_sync_rail()` ไฮไลต์ตาม mode/kind (เรียกท้าย `_sync_options` จุดเดียว), ซ่อน toggle ไฟล์/URL นอกโหมดสเต็ม, ล็อก rail ตอนมีงาน, หน้าต่าง `900x820`
- **logic งานไม่แตะเลย** (`_start`/`_run_*`/worker เหมือนเดิม)
- **ตรวจของจริง**: สคริปต์ `verify_rail.py` บน mainloop — rail เริ่มต้น url, สลับ file/stems/url ถูกทุก state, toggle โผล่เฉพาะสเต็ม, กด hero pill ตรง rail ซิงก์ตาม, งาน trim จริงจบ "เสร็จสิ้น" + output ครบ; แคปทุก view แล้ว
- **Tests**: full suite **216 tests ผ่าน** (skipped 2 = network); `USER_GUIDE` §3 เพิ่มรางซ้ายแล้ว
- **ค้าง**: ผู้ใช้ลองกดเอง + scale 125/150% (ยังไม่ bump version)

## ทำวันนี้ (2026-09-24) — กลับมาใช้ม่วงเดิม (ยังไม่ bump version)

- ผู้ใช้ไม่เอามิ้นต์ → revert `theme.py` กลับ Midnight Amethyst เดิมทั้งไฟล์ + เอา `ON_ACCENT` ออกจาก `ui.py` (ปุ่ม accent กลับตัวหนังสือขาว)
- ของที่เก็บไว้จากรอบมิ้นต์: จุดสีหน้าหัวข้อ section (ตอนนี้เป็นจุดม่วง), hover ปุ่มเป็น glow สว่าง (`ACCENT_GLOW`)
- ตรวจของจริง + full suite **216 tests ผ่าน** (skipped 2 = network)

## ทำวันนี้ (2026-09-24) — เปลี่ยนธีมเป็น Emerald Night: ดาร์กพรีเมียม + มิ้นต์ (ยังไม่ bump version)

- **เหตุผล**: ผู้ใช้ไม่ชอบม่วง เลือกดาร์กพรีเมียม + เขียวมิ้นต์
- **เปลี่ยนใน `clipora/ui_components/theme.py`**: accent ม่วง → มิ้นต์ (`ACCENT #10b981`, hover `#34d399`, glow `#6ee7b7`, soft `#0b2e26`), เพิ่ม `ON_ACCENT #04352b` (ตัวหนังสือเข้มบนปุ่มมิ้นต์), `SUCCESS` → `#4ade80` (ให้ต่างจาก accent ตอน success flash), พื้นผิวดาร์กเกลี่ยใหม่ให้มีมิติ (`CARD/FIELD/BORDER/SECONDARY` สว่างขึ้นเล็กน้อย), `MENU_ACTIVE_FG` เป็นสีเข้ม
- **ตามใน `clipora/ui.py`**: ปุ่ม accent ทุกแบบ (เริ่ม/dialog/สนับสนุน) + ปุ่มโหมดที่เลือก + toggle ไฟล์/URL ใช้ตัวหนังสือเข้ม, section title มีจุดมิ้นต์หน้าหัวข้อ; เอฟเฟกต์ motion เดิมคำนวณสีจาก theme ตอนรันเลยตามมาเอง (hover glow/press/flash/pulse)
- **ตรวจของจริง**: แคปทุก state (url+video, file+audio+details, stems, จบงาน) — เจอหน้าต่างม่วงเก่าค้างจากสคริปต์รอบแรกที่ crash ก่อน destroy (เคลียร์โปรเซสแล้ว, สคริปต์ verify รันจบ destroy ครบเลยไม่ค้าง)
- **Tests**: full suite **216 tests ผ่าน** (skipped 2 = network, ไม่ต้องแก้เทสต์เพราะไม่มี hardcode สีม่วงในเทสต์)
- **ค้าง**: ผู้ใช้ดูของจริงที่เครื่องว่าถูกใจไหม (ยังไม่ bump version)

## ทำวันนี้ (2026-09-24) — เพิ่ม motion/animation ทั่วแอป (ยังไม่ bump version)

- **ของใหม่**: `clipora/ui_components/motion.py` (pure + test ได้โดยไม่ต้องมีจอ: `mix_color`/`easing`/`Tween`/`Pulse`/`fade_in_window`) + `tests/test_motion.py` 13 tests
- **เอฟเฟกต์ที่ต่อแล้ว** (main thread ผ่าน `after` ทั้งหมด, logic งานไม่แตะ):
  - ปุ่มเริ่ม: hover glow (`ACCENT` → `ACCENT_GLOW`), กดยุบเข้ม, ปล่อยเด้งกลับ, งานสำเร็จแฟลชเขียวแล้วกลับม่วง
  - ปุ่มโหมด: เปลี่ยนโหมดแล้ว hero box กระพริบ glow อ่อน (`FIELD` → `ACCENT_SOFT` → `FIELD`)
  - progress bar: pulse ม่วงอ่อน-เข้มระหว่างงาน หยุดและคืนสีเมื่อจบ/ยกเลิก/พัง (`_finish_job` จุดเดียว)
  - dialog ทั้ง 7 ตัว (Overwrite/Error/AppUpdate/Disclaimer/Donate/Dmca/ToolSetup) fade-in ตอนเปิด
  - toast สไลด์ขึ้น + fade-in
- **ตรวจของจริง**: สคริปต์ `verify_motion.py` บน mainloop — hover/press/release/hero-flash/toast/dialog/pulse/success-flash ผ่านทุก assert, แคปภาพยืนยัน (จับช็อตปุ่มเขียวกลางแฟลชได้ด้วย)
- **Tests**: full suite **216 tests ผ่าน** (203 เดิม + 13 motion, skipped 2 = network)
- **ค้าง**: ผู้ใช้ลอง hover/กดจริงที่เครื่อง + display scale ต่างๆ ว่าเอฟเฟกต์ลื่นไหม (16ms/frame บน Tk มาตรฐาน)

## ทำวันนี้ (2026-09-24) — ดีไซน์ UI ใหม่ทั้งหน้าหลัก (ยังไม่ bump version)

- **เหตุผล**: หน้าหลักเดิมดูรก (การ์ดขอบหนา + แถบม่วง + ป้ายตัวเลข 01/02/03, error แดงโชว์ตั้งแต่เปิดแอป, ตัวเลือกอัดแน่นต้องสกรอลล์)
- **ดีไซน์ใหม่** (`clipora/ui.py` อย่างเดียว ไม่แตะ logic/worker): top bar แบบ slim (โลโก้ + `v{__version__}` + ปุ่มสนับสนุน + ☰), ปุ่มโหมด 3 ปุ่มใหญ่พร้อมคำอธิบาย 1 บรรทัด, section ไร้กรอบคั่นด้วยเส้น hairline, คุณภาพ/เฟรมเรต/trim ย้ายเข้าปุ่ม **▸ ตัวเลือกเพิ่มเติม** แบบพับได้, ลิงก์ DMCA ย้ายจากหน้าหลักเข้า ☰ เมนู, footer เหลือเวอร์ชัน + ertyu.dev, หน้าต่าง `780x820` พอดีจอไม่ต้องสกรอลล์
- **บั๊กที่เจอระหว่างทาง (แก้แล้ว)**:
  - error แดงโชว์ตั้งแต่เปิดแอป — สาเหตุคือ `<FocusOut>` ยิงตอนหน้าต่าง map ครั้งแรก → แก้ให้ FocusOut เตือนเฉพาะช่องที่มีข้อความ (`_validate_source_or_hide`) และบังคับ `_validate_all()` ตอนกดเริ่มงานจริง (เดิม `_validate_all` ไม่มีคนเรียกเลย)
  - ช่อง trim พื้นขาว — ลืมใส่ `style='Dark.TEntry'`
  - checkbox indicator ขาว — clam ใช้ `indicatorbackground` ไม่ใช่ `indicatorcolor` (แก้ทั้ง `TCheckbutton`/`Plain.TCheckbutton`, ติ๊กถูก = กล่องม่วง)
  - ปุ่มสนับสนุนขึ้นกล่อง tofu — ฟอนต์ไม่มี glyph ♥ → ตัดเหลือคำว่า "สนับสนุน"
- **ตรวจของจริง**: แคป before/after เทียบ, สคริปต์ `verify_gui.py` บน mainloop จริง — toggle details/trim/stems visibility ถูกทุก state, งาน trim จริง 6วิ → ออก 2.0วิเป๊ะ สถานะ "เสร็จสิ้น" + result panel ขึ้น
- **Tests**: full suite **203 tests ผ่าน** (skipped 2 = network); `USER_GUIDE` §3/§11 อัปเดตตาม UI ใหม่แล้ว
- **ค้าง**: manual GUI smoke บนหลาย display scale (100/125/150%) ยังไม่ได้ทำ — ผู้ใช้ช่วยดูอีกแรง

## ทำวันนี้ (2026-09-24) — ต่อสาย trim + disk-check/cleanup + ปรับคำ GitHub ให้รัดกุม

- **ตรวจด้วยเทสต์ก่อนทำ**: full suite 181 ผ่าน (skipped 2 = network) แล้วยืนยันว่า trim/batch/disk-check/cleanup/limiter ใช้ไม่ได้จริง — ช่อง trim ไม่มี `.get()` เลย (`ui.py`), ไม่มีโค้ดคิวงานทั้ง repo, `check_disk_space`/`cleanup_orphaned_*` มีแต่ไม่มีจุดเรียก, `separator_environment()` ถูกเรียกแบบไม่ส่ง limit; เทสต์ใหม่จับได้ด้วยว่า `ffmpeg.py` เรียก `shutil` แต่ไม่เคย import (NameError แฝง) → เติม `import shutil` แล้ว
- **ข — trim ใช้ได้จริง (งานไฟล์ในเครื่อง โหมดแยกเสียง/แปลงวิดีโอ)**: `parse_trim_seconds()` (วินาที/`MM:SS`/`HH:MM:SS`, ค่าว่าง = ไม่ตัด) + `normalize_trim()` (จุดเริ่มเกินไฟล์ = error, ระยะเวลาเกิน = clamp, คืน effective duration ให้ progress) ใน `clipora/ffmpeg.py`; `JobSpec` เพิ่ม `trim_start/trim_duration`; `_start_local` ตรวจรูปแบบก่อนเริ่ม (เตือนผ่าน messagebox), `_run_local` ตรวจขอบเขตหลัง probe (error เข้า `ErrorDialog` ที่มีปุ่ม copy); แถว trim ซ่อนในโหมดสเต็ม/URL; ป้ายฟิลด์ที่สองแก้เป็น "ระยะเวลา (เว้นว่าง = ทั้งหมด)"
- **ค — disk-check + cleanup ถูกเรียกจริง**: `_prepare_destination()` ใน `ui.py` ล้าง orphaned workspaces (import + separator, พลาดไม่บล็อกงาน) แล้วตรวจพื้นที่ดิสก์ก่อนเริ่มงานทุกครั้ง (ไฟล์ในเครื่อง = `check_disk_space`, ลิงก์ = `check_destination_disk_space`, เต็ม = เตือนแล้วไม่เริ่มงาน)
- **Tests**: +22 tests (parse/normalize/command ใน `test_ffmpeg.py`, trim end-to-end กับ fixture จริงใน `test_ffmpeg_integration.py`, disk/orphan ใน `tests/test_maintenance.py` ไฟล์ใหม่) → full suite **203 tests ผ่าน** (skipped 2 = network)
- **ก — ปรับคำ GitHub**: `README` กระชับ (intro 2 บรรทัด, มีอะไรใหม่ 0.6.3, วิธีตรวจ `.sha256`, แก้ 3 จุดที่ขัดของจริง: สิทธิ์ admin/รวมเครื่องมือ/portable), `release.yml` ใช้ release notes ภาษาไทยคงที่แทน `--generate-notes`, `SECURITY.md` เป็นตารางเวอร์ชันที่รองรับ, `USER_GUIDE` เพิ่มวิธีใช้ trim + disk/cleanup + ปุ่ม copy log, `DEVELOPMENT` แก้ trigger `pc-v*`/per-machine/trim ที่ทำแล้ว, `ACTIVITY_LOG` ติ๊กตามจริง (batch/limiter ยังไม่ทำ), `clipora.manifest` sync 0.6.3.0
- **ค้าง**: batch queue (ไม่มีโค้ด ต้องเริ่มใหม่), trim สำหรับงาน URL/stems, CPU limiter (เรียกแบบจำกัด), About repo บนเว็บ (description/topics ต้องกดเอง) — ไม่ bump version รอบนี้ (ยังไม่ปล่อย release)

## ทำวันนี้ (2026-09-21) — Quick fix: TikTok `Unexpected response from webpage request`

- **สาเหตุ**: user รายงานดาวน์โหลด TikTok ล้มเหลว (`[TikTok] 7673293790857235733: Unexpected response from webpage request; please report... Confirm you are on the latest version using yt-dlp -U`) — ตรงกับ upstream `yt-dlp#17407` (duplicate/site:tiktok บน stable `2026.07.04` ซึ่งเป็น pin ปัจจุบัน) และ `#17604` (ยัง open บน nightly `2026.08.30`, stack ชี้ `tiktok.py _solve_challenge_and_set_cookies`) → เว็บเปลี่ยนระบบ ไม่ใช่ลิงก์ private เสมอไป
- **ปัญหาในแอป**: `_run_import_process` จัด error นี้เป็น generic `URLImportError` ("ลิงก์อาจไม่เป็นสาธารณะ...") ทำให้เข้าใจผิด และ `_run_import_with_fallback` ไม่ retry (ถูกแล้ว เพราะต้องแก้ extractor ต้นทาง)
- **แก้ (ไม่ bump pin ตามที่ user เลือก)**: เพิ่ม `_EXTRACTOR_BROKEN_SIGNATURES` + `is_extractor_broken_error()` + `URLExtractorBroken` (subclass ของ `URLImportError`, ข้อความไทยชี้นำกด "อัปเดต yt-dlp (Ctrl+U)") ใน `clipora/importer.py`; เช็คใน `_run_import_process` หลัง block-check จึง fail-fast โดยไม่ retry
- **Tests**: +4 tests ใน `tests/test_importer.py` (`ExtractorBrokenDetectionTests`: detect/ignore/message/fail-fast ไม่ retry)
- **Docs**: `docs/TROUBLESHOOTING.md` เพิ่มหัวข้อ extractor-broken + วิธีแก้; ไม่เปลี่ยน pin/SHA/version จึงไม่ต้อง sync packaging
- **Release**: bump PC 0.6.2 → **0.6.3** (patch — ข้อความ extractor-broken ของ TikTok); sync `__init__.py`, `version_info.txt`, `.iss`, README แล้ว; full suite 181 tests ผ่าน (skipped 2 = network) + test_packaging 6/6; commit → tag `pc-v0.6.3` → push → รอ `build-windows` job ปล่อย Setup + portable ZIP + `.sha256` ขึ้น release `pc-v0.6.3` เพื่อให้ตัวเช็คอัปเดตในแอปแจ้งเตือนผู้ใช้

## สถานะโดยรวม

- **RELEASE PC 0.6.0** — UI/UX redesign (ธีม Midnight Amethyst + stepper 3 ขั้น + result panel) + security hardening (zip-slip guard ใน dependencies, ยืนยันสิทธิ์); 163 tests ผ่าน (skipped 4 = network) + test_packaging 6/6

- ฟีเจอร์ **แยกสเต็มเสียง (stems)** ผ่านการ implement ครบและทดสอบผ่านแล้ว
- ฟีเจอร์ **อัปเดต yt-dlp** (ปุ่มในแอป + ตรวจอัตโนมัติตอนเปิดแอป) implement ครบและทดสอบผ่านแล้ว
- **PC: auto-retry fallback เมื่อโดนบล็อก (HTTP 403/429/กัน bot)** — implement ครบ 30 tests ผ่าน (รายละเอียดด้านล่าง)
- ชุดเทสต์เต็ม: **138 tests ผ่าน** (skipped 2 = network) — รันบน Python 3.13 (venv สร้างใหม่)
- ทดสอบจริง end-to-end ฟีเจอร์ stems แล้ว (Demucs บน CPU, เอาต์พุต `_vocals.mp3` + `_instrumental.mp3` + `_stems.zip`)
- **ติดตั้งเครื่องมือ separator จริงแล้ว** — `%LOCALAPPDATA%\Clipora\tools\separator` (~209 MB), `test_separator_integration.py` รันผ่าน 2/2
- **ทดสอบจริง flow อัปเดต yt-dlp แล้ว** — วาง exe รุ่น 2026.06.09 ลง managed tools แล้ว `update_ytdlp()` อัปเดตเป็น 2026.07.04 ผ่าน (download → checksum → atomic replace → record)
- **อัปเดต docs แล้ว** — `THIRD_PARTY_NOTICES.md` (เพิ่ม separator toolchain + wheel table), `README.md`, `docs/USER_GUIDE.md`

## ทำวันนี้ (2026-08-19) — รอบที่ 2

- **PC: แก้ไฟล์ดาวน์โหลดเปิดไม่ได้ error 0x80070005 (E_ACCESSDENIED)** — ผู้ใช้รายงานไฟล์ผลลัพธ์ที่ดาวน์โหลดจาก URL มี ACL ที่ผู้ใช้ปัจจุบันไม่มีสิทธิ์ (owner SID resolve ไม่ได้, `icacls`/`Get-Acl` อ่านไม่ออก, ไม่ใช่ EFS/OneDrive/reparse) — สาเหตุคือ `finalize_import_output` ใช้ `os.link` (hard link) ที่ลอก security descriptor จากไฟล์ต้นทางใน workspace ซึ่งอาจไม่รวมสิทธิ์ผู้ใช้ปัจจุบัน → **แก้**: เพิ่ม `normalize_output_permissions()` (รัน `icacls <file> /grant <user>:(F)` ผ่าน argument list ไม่ใช้ shell, ครอบ try/except, ทำงานเฉพาะ Windows) เรียกหลังสร้าง target ทุกครั้งใน `finalize_import_output`
- **PC: เพิ่มการถามเขียนทับในโหมดดาวน์โหลด URL** — เดิมเมื่อไฟล์ชื่อเดียวกันมีอยู่ `finalize_import_output` สร้างชื่อ `(N)` ให้อัตโนมัติ → **แก้**: เพิ่มพารามิเตอร์ `on_conflict: Callable[[Path], bool]` ให้ `finalize_import_output`/`import_url`; UI ส่ง callback ที่ถามผ่าน `OverwriteDialog` บน main thread (ใช้ `self.after` + `threading.Event` ตามกติกา worker ต้องไม่แตะ Tk); ถ้าเลือกเขียนทับ → ลบไฟล์เก่าแล้วสร้างใหม่, เลือกเก็บทั้งสองไฟล์/ยกเลิก → คงชื่อ `(N)`
- **PC: UI/UX ใหม่ 4 ด้าน**:
  - **Theme/visual**: ย้าย palette ไป `clipora/ui_components/theme.py` (ค่าคงที่แบบมีชื่อ: TOP_BAR_BG, SECONDARY_BG, DISABLED_FG ฯลฯ) — ui.py/widgets.py/dialogs.py อ้างใช้เดียวกัน; ลด hardcoded hex
  - **Layout**: เพิ่ม **stepper 3 ขั้น** (1 แหล่งสื่อ → 2 ที่บันทึก → 3 รูปแบบ) ด้านบน content, ขยับการ์ดลง 1 แถว; `_update_stepper()` เปลี่ยนสถานะตามการกรอกจริง (inactive/done)
  - **UX flow**: หลังงานเสร็จ action bar แสดง **result panel** (ชื่อไฟล์ + ขนาดรวม + ปุ่ม "เปิดโฟลเดอร์" / "เปิดไฟล์") แทน toast อย่างเดียว; `_show_result()`/`_open_result_folder()`/`_open_result_file()` ใช้ `os.startfile`
  - **Dialog เขียนทับ**: สร้าง `clipora/ui_components/dialogs.py` — `OverwriteDialog` (Toplevel ธีมเดียวกับแอป, แสดงชื่อไฟล์ + ขนาดเดิม + ขนาดใหม่, ปุ่ม เขียนทับ/เก็บทั้งสองไฟล์/ยกเลิก) ใช้แทน `messagebox.askyesno` ใน `_start_local`/`_start_stems_local` และ URL conflict
  - ย้าย `format_file_size` ไป `clipora/ui_components/format.py` (เลี่ยง circular import ระหว่าง ui ↔ dialogs)
- **Tests**: +7 tests ใน `tests/test_importer.py` (overwrite on_conflict True/False, fallback เมื่อ unlink ล้มเหลว, icacls เรียกบน Windows, ข้ามบน non-Windows, อดทนต่อ icacls ล้มเหลว); `tests/test_ui_helpers.py` ยังผ่าน (format_file_size import จาก path ใหม่)
- **Release**: ไม่ bump version — ยัง 0.5.6 แล้ว push (commit `ec43cc9`) + `gh workflow run` (run `32254934177` build-windows ผ่าน) → upload `--clobber` ทับ 4 assets เดิมบน release `pc-v0.5.6` เรียบร้อย (สร้าง 2026-08-19 12:56Z); full suite 161 tests ผ่าน (skipped 4 = network) + `test_packaging` 6/6 ผ่าน
- **หมายเหตุ**: พบไฟล์ค้างใน working tree ที่ยังไม่เคย commit — `clipora/ui_components/widgets.py` + `__init__.py` (ui.py import อยู่แล้ว) ถูก add เข้า commit ด้วย; ส่วน mobile changes ค้าง (README, app_state.dart, yt-dlp AAR) ถูก stash/restore กลับไว้เฉยๆ ไม่แตะ
- **หมายเหตุ 2**: ไม่สามารถส่งอีเมลแจ้งผู้ใช้ได้ — Outlook COM มีเฉพาะแอป แต่ไม่มี mail profile/bัญชี configured (CreateItem คืน null, GetNamespace ค้างรอโปรไฟล์) จึงไม่มี SMTP ให้ใช้
- **กู้ไฟล์เดิม ACL แตกสำเร็จ** — ผู้ใช้รัน `icacls /grant` แบบ Administrator เอง (คำสั่งเดิมมี syntax bug `$u:(F)` → PowerShell ตีความเป็น drive reference ต้องใช้ `${u}:(F)`)

## ทำวันนี้ (2026-08-20) — รอบที่ 4: audit ความปลอดภัย + แก้ช่องโหว่

- **Audit ความปลอดภัย (findings 1–10)** ตรวจทั้ง PC + Mobile (ไม่มี secrets ใน git history; subprocess ทั้งหมดใช้ argument list ไม่มี shell=True):
  - Medium: Mobile ไม่ validate URL → SSRF/เข้าถึงเครือข่ายภายใน; URL ขึ้นต้น `-` → yt-dlp option injection; PC `validate_url` เช็ค string อย่างเดียว (ข้าม DNS rebinding/redirect); Mobile path traversal ผ่านชื่อไฟล์จาก provider ใน `copyUriToCache`; PC `zipfile.extractall` รับ archive จาก network (zip-slip) ผิดข้อกำหนด SECURITY.md
  - Low: `http://` ยังอนุญาต (ไม่บังคับ HTTPS); yt-dlp auto-update ใช้ TOFU checksum; mobile ไม่มี max-filesize; `_cleanupPickCache` ใช้ prefix match; env `PATH`/`CLIPORA_*` override
- **แก้แล้ว (ตามที่ผู้ใช้เลือก: ข้อ 1, 2, 4, 5)** — ข้ามข้อ 3 (PC DNS rebinding/redirect ต้องเพิ่ม resolve+IP-check ก่อนขอ redirects หรือสอบสวนตัวเลือกเพิ่ม):

### Mobile
- **ข้อ 1 + 2: URL validation** — เพิ่ม `AppState.validateDownloadUrl()` ใน `mobile/lib/app_state.dart` (scheme ต้อง http/https, มี host, ไม่มี userinfo, port 1–65535, ปฏิเสธ localhost/.localhost และ IP literal ส่วนตัว: 0/8, 10/8, 100.64/10, 127/8, 169.254/16, 172.16/12, 192.0.0/24, 192.0.2/24, 192.168/16, 198.18/15, 198.51.100/24, 203.0.113/24, 224+/4, IPv6 ::, ::1, fc00::/7, fe80::/10, ff00::/8, 64:ff9b::/96, 2001:db8::/32) — ใช้ใน `startUrlDownload` + `home_screen._startUrl` (แทนการเช็ค scheme เดิม); การบังคับ http(s):// ทำให้ URL ขึ้นต้นด้วย `-` เป็นไปไม่ได้ → กัน option injection โดยไม่ต้องใช้ตัวคั่น `--`; **เพิ่มเติม (หลัง reviewer)**: ปฏิเสธ hostname รูป encode อื่นของ IP ส่วนตัว (hex `0x7f000001`, decimal `2130706433`, octal `0177.0.0.1`, shorthand `127.1`, `[::ffff:127.1]`) — hostname ตัวเลขล้วนไม่เคยเป็นโดเมนสาธารณะใน DNS
- **Defense-in-depth ฝั่ง Kotlin** — `MainActivity.kt`: เพิ่ม `validateDownloadUrl()` (java.net.URI) + `isNonPublicIpLiteral()/isNonPublicIpv4()/isNonPublicIpv6()` เรียกใน `handleDownload` ก่อนสร้าง `YtDlpRequest`
- **ข้อ 4: path traversal** — `copyUriToCache` ตัดชื่อไฟล์ให้เหลือ basename (`File(rawName).name`) + ตรวจ `canonicalPath` ต้องอยู่ใต้ cacheDir ก่อนเขียน
- **Tests** — +9 tests ใน `mobile/test/app_state_test.dart` (accept/trim, public IP, non-http scheme, SSRF IPs, credentials/port, dash-prefix, hostname-less); `flutter analyze` + `flutter test` ผ่าน 22/22; `flutter build apk --debug` ผ่าน (Kotlin compile OK)
- **Docs** — `mobile/README.md` เพิ่มข้อควรรู้ "ลิงก์ต้องเป็น http/https สาธารณะ" (กัน SSRF + option injection, เช็คสองชั้น)

### PC
- **ข้อ 5: zip-slip** — `clipora/dependencies.py` เพิ่ม `_safe_extractall()` ตรวจทุก member ก่อน `extractall` (ปฏิเสธชื่อ absolute, ขึ้นต้น `/`, มี `..`, และที่ resolve หลุดออกจาก destination) ใช้แทนที่ `python-embed` + `python-wheel`; ถ้าผิดยก `DependencyInstallError`
- **Tests** — +2 tests ใน `tests/test_dependencies.py` (python-embed `../evil.txt`, python-wheel absolute path); suite PC ทั้งหมด 163 tests ผ่าน (skipped 4 = network)
- ยังไม่ทำ: ข้อ 3 (DNS rebinding/redirect SSRF ฝั่ง PC), ข้อ 6–10 (low) — รอตัดสินใจขอบเขตเพิ่ม
- **Release**: bump PC 0.5.6 → **0.6.0** (minor — UI redesign รอบ 3 + security fixes รอบ 4); sync `__init__.py`, `version_info.txt`, `.iss`, README แล้ว; full suite 163 tests ผ่าน (skipped 4) + test_packaging 6/6; commit → tag `pc-v0.6.0` → push → รอ `build-windows` job

## ทำวันนี้ (2026-08-20) — รอบที่ 3: redesign UI/UX ทั้งแอป

- **ธีมใหม่ "Midnight Amethyst"** — `clipora/ui_components/theme.py` ถูกเขียนใหม่ทั้ง palette: ฐานดำน้ำเงินเข้ม (`#0b0e16`), การ์ด `#141926`, ม่วง accent เดิม + เพิ่มชั้นสีใหม่ (`ACCENT_SOFT`, `ACCENT_GLOW`, `STEP_*`, `DISABLED_BG`, `FONT_SIZE_*`) ให้ทุกส่วนอ่านง่ายบนพื้นหลังมืด; ui.py/widgets.py/dialogs.py/setup_ui.py import constants กลางทั้งหมด (ลบ hardcoded hex ค้างใน setup_ui: bg `#090d15`, checkbox `#141a26` ฯลฯ)
- **Layout หลักใหม่**:
  - Top bar: โลโก้ในกรอบม่วง (`ACCENT_SOFT`) + ชื่อแอป + subtitle "แปลงวิดีโอ • แยกเสียง • ดาวน์โหลด" 2 บรรทัด
  - การ์ด 3 ใบ: มีแถบ accent ม่วง 3px ด้านซ้าย (`_make_card` ใช้ `outer` bg=BORDER + accent frame column 0) โดยไม่ต้องย้าย grid ของ content ภายใน
  - Stepper: เปลี่ยนเป็น pill ต่อเนื่องแบบ connector เต็มแถว + `StepperCaptionActive.TLabel` (caption สว่างขึ้นเมื่อ step สำเร็จ)
  - Action bar: **ปุ่มเริ่มงานย้ายขึ้นบนสุด** (ใหญ่เต็มแถว) progress/สถานะ/result panel อยู่ล่าง — ปุ่มหลักโดดเด่นก่อน
  - Footer: แยก frame มี padding สม่ำเสมอ
- **Widgets**: Toast มีแถบสี accent ซ้ายตาม type (info/success/warning/error); DropZone ใช้สีธีมกลาง
- **Dialogs**: OverwriteDialog/Disclaimer/Donate/Dmca เพิ่มแถบ accent ซ้าย + ใช้ theme constants; setup_ui ใช้ `BG`/`CARD`/`FIELD`/`TEXT`
- **ทดสอบ**: `compileall` ผ่าน, app เปิดได้ (PID รันแล้ว kill), full suite **161 tests ผ่าน** (skipped 4 = network); screenshot ไว้ที่ `C:\Users\user\AppData\Local\Temp\opencode\clipora_ui_v2.png` ให้ผู้ใช้ยืนยัน visual ก่อน release
- **Release**: ยังไม่ปล่อย — รอผู้ใช้ยืนยันผล visual แล้วค่อย clobber release `pc-v0.5.6` รอบ 2 → ทั้ง `.mp4` (20,740,750 B) และ `.mp3` (7,638,957 B) เปิดอ่านได้แล้ว

## ทำวันนี้ (2026-08-19)

- **PC: แจ้งเตือนเมื่อโดนบล็อกระดับเครือข่าย/ISP** — `URLNetworkBlocked` (subclass ของ `URLImportError`) + `is_network_block_error()` detect `getaddrinfo failed`/`failed to resolve`/`network is unreachable` ฯลฯ → แสดงข้อความชี้ทางแก้ (เปลี่ยน DNS 1.1.1.1/8.8.8.8 หรือใช้ VPN/proxy) และ **ไม่ retry** (DNS แก้ด้วย impersonation ไม่ได้); ตรวจใน `_run_import_process` ก่อน `is_block_error`
- **PC: แก้ bug fallback append impersonation ซ้ำไม่รู้จบ** — เดิมถ้าทุกชั้นโดนบล็อก loop จะ append `--impersonate` ทุกครั้ง (index+1 == len) → เพิ่ม flag `impersonation_appended` ป้องกัน; +test  regression (ตอนนี้พยายาม 3 ครั้ง: clean → extractor args → impersonation แล้วหยุด)
- **PC: auto-update yt-dlp ทันที** — ตรวจอัตโนมัติหลังเปิดแอป 3 วิ ถ้าพบเวอร์ชันใหม่ อัปเดตให้เลยโดยไม่ถาม (ปุ่ม manual ยังถามยืนยันอยู่) — แก้ `ui.py` `_ytdlp_check_done`
- **PC: เพิ่ม YouTube `player_client` fallback** — `_SITE_EXTRACTOR_ARGS` + `site_workaround_extractor_args()` → `--extractor-args youtube:player_client=android,web_embedded,tv` ใส่เป็นชั้นกลางของ fallback chain (clean → headers → extractor args → impersonation) — workaround ที่รู้จักกันดีของ 403/"not a bot" ของ YouTube โดยไม่ใช้ cookies
- **PC: auto-retry fallback เมื่อ URL download โดนบล็อก (HTTP 403/429/กัน bot)** — ผู้ใช้รายงาน `HTTP Error 403: Forbidden` (บางเคส DNS resolve ไม่ได้ด้วย → น่าจะถูกบล็อกที่ระดับเครือข่าย/ISP) — เพิ่มใน `clipora/importer.py`:
  - `URLImportBlocked` (subclass ของ `URLImportError`) — ยกเมื่อ yt-dlp output มี signature บล็อก
  - `is_block_error()` — detect 403/429/"not a bot"/"unusual traffic"/captcha/robot ฯลฯ
  - `site_workaround_headers()` — per-site `--add-header` (TikTok → `Referer:https://www.tiktok.com/` mirror จาก mobile)
  - `browser_impersonation_args()` — `--impersonate chrome`
  - `ytdlp_supports_impersonation()` — รัน `--list-impersonate-targets` ครั้งเดียวแล้ว cache (กัน pip module ที่ไม่มี curl_cffi; exe ทางการมี curl_cffi ในตัว)
  - `build_import_command(..., extra_args=())` — ใส่ extra args ก่อน `-- url`
  - `_run_import_with_fallback()` — ลูป 3 รอบ: clean → +headers → +impersonation; ลบ partial ใน workspace ก่อน retry; non-block error fail ทันที
  - `import_url()` / `import_audio_for_processing()` — ใช้ fallback chain
  - UI ไม่เปลี่ยน (retry เงียบ) — ตามที่ผู้ใช้เลือก
  - Tests: +10 tests ใหม่ใน `tests/test_importer.py` (headers, block detection, impersonation args, extra_args ตำแหน่ง, retry chain, non-block fail, unsupported impersonation)
  - Docs: `USER_GUIDE.md` (โหมด URL), `TROUBLESHOOTING.md` (หัวข้อโดนบล็อก + เช็ค DNS)

## ทำวันนี้ (2026-08-17)

- แก้ venv เสีย (ชี้ไป Python 3.9 ของ user อื่น) → สร้างใหม่ด้วย Python 3.13 + `requirements-dev.txt`
- แก้ bug ใน `tests/test_separator_integration.py`: `setUpClass` ใช้ `with tempfile.TemporaryDirectory()` ซึ่งลบไฟล์ source ก่อน test รัน → เปลี่ยนเป็นเก็บ tempdir ใน class และ `tearDownClass` cleanup
- **แยกเวอร์ชัน PC/Mobile**: PC กลับเป็น `0.5.1` (mobile คง `1.0.1`) — แก้ `__init__.py`, UA, iss, version_info, README
- **แก้ CI ล้ม**: `test_donate.py` เช็ค `assets/` (gitignored ไม่มีใน CI) → ลบ assert นั้น
- **Donate QR ใช้ไฟล์ที่ commit ตรง ๆ แล้ว**: เดิมเก็บ QR เป็น secret `CLIPORA_DONATE_QR_BASE64` และ decode ใน CI — เปลี่ยนมา commit `assets/donate-qr.png` ไว้ใน repo (เลิก gitignore, ลบ step decode จาก workflow, ลบ `scripts/print_donate_secret.ps1`) เพื่อให้ทุก build มี QR แน่นอน
- **แยกสเต็ม → อัด zip**: `separate_audio()` สร้าง `{ชื่อ}_stems.zip` รวมทุกสเต็ม หลังแยกเสร็จ (ไฟล์แยกยังอยู่) — `create_stems_zip()`, `separate_output_zip_path()`, UI เช็ค overwrite zip ด้วย, test 3 ตัวใหม่ + integration อัปเดต (138 tests ผ่าน)
- **แก้ QR โดเนทไม่ขึ้น + ขึ้นเวอร์ชัน 0.5.2**: `DonateDialog` ใช้ `ttk.Label` style `Card.TFrame` (Frame layout ไม่มี label element) ทำให้ label รูป QR หดเหลือ 1x1 → เปลี่ยนเป็น `Card.TLabel`; เปลี่ยน QR จาก CI secret มาเป็นรูป commit ตรง ๆ; bump ทุกที่ (`__init__`, iss, manifest, version_info, UA ×2, README)
- **เพิ่มตัวโหลดแบบ ZIP (portable) ใน release**: workflow `release.yml` แพ็ค `dist/Clipora` → `Clipora-<ver>-x64.zip` (+ `.sha256`) หลัง build installer แล้วอัปโหลดขึ้น release คู่กับตัวติดตั้ง; อัปเดต README ตอนติดตั้ง
- **Mobile: เพิ่มนำเข้า Cookies (ฟรี) แก้ APK โหลดคลิปไม่ได้**: สาเหตุคือ `yt-dlp-android` ฟรีไม่มี curl-cffi/TLS impersonation (YouTube ตรวจ TLS fingerprint บล็อก) + yt-dlp ฝังเป็น 2026.06.09 — เพิ่ม `pickCookiesFile` (native channel, request 9102), `importCookies()/clearCookies()` เก็บที่ `{appDir}/clipora/cookies.txt`, ส่ง `--cookies <path>` ในทุก URL download, UI ใน `_urlPanel`; bump mobile 1.0.2 (flutter analyze/test ผ่าน)

## ฟีเจอร์โดเนท PromptPay (เพิ่ม 2026-08-17)

- ปุ่ม **โดเนท** ที่ header (คอลัมน์ 5) → เปิด `DonateDialog` แสดง QR PromptPay + ข้อความ
- `clipora/donate.py` (ใหม่): `donate_image_path()` ค้นหา `donate-qr.png` จาก `_MEIPASS` / หลัง exe / `assets/` (source)
- QR asset: วางต้นฉบับที่ `assets/pay/promptpayQr.jpg` แล้วแปลงเป็น `assets/donate-qr.png` (Tk อ่าน PNG/GIF ได้ ไม่รองรับ JPG, runtime stdlib-only) ขนาด 320x428
- `packaging/clipora.spec`: เพิ่ม `assets/donate-qr.png` เข้า `datas` (ถ้ามีไฟล์)
- `tests/test_donate.py` (ใหม่): 3 tests ค้นหา asset / ไม่เจอคืน None / bundled มี priority

## ฟีเจอร์อัปเดต yt-dlp (เพิ่ม 2026-08-16)

### การตัดสินใจ/เหตุผล
- ผู้ใช้เลือก: **ปุ่มอัปเดต yt-dlp ในแอป + ตรวจอัตโนมัติตอนเปิดแอป**
- yt-dlp ถูก pin ไว้ที่ `2026.07.04` ใน `dependencies.py` (ยังเป็นเวอร์ชันล่าสุด ณ วันที่ตรวจ — GitHub API)
- ไม่มีกลไก auto-update มาก่อน และ `dependencies_to_install()` จะข้ามถ้ามีอยู่แล้ว
- การอัปเดตเป็นกรณีพิเศษที่ยอมให้ใช้ "ล่าสุด" (ต่างจากกติกา pin ทุกอย่าง) — ยืนยัน checksum จาก `SHA2-256SUMS` ของ GitHub เสมอ

### ไฟล์ที่แก้/เพิ่ม
| ไฟล์                                | งาน                                                                                                                                                                                                                                                                                                                                                                                                                   |
| ---------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `clipora/ytdlp_update.py` (ใหม่)    | `latest_ytdlp_version()` (GitHub API `releases/latest`), `installed_ytdlp_version()` (อ่านจาก exe + `installed.json`), `is_newer_available()`, `parse_ytdlp_version()`, `update_ytdlp()` — ดาวน์โหลด `yt-dlp.exe` + `SHA2-256SUMS`, ตรวจ sha256, `os.replace` แบบ atomic ลง `managed_tools_dir()/yt-dlp.exe`, เขียน `installed.json` ใหม่ผ่าน `_write_install_record`; HTTPS เท่านั้น, รองรับ progress callback + cancel check |
| `clipora/ui.py`                    | ปุ่ม "อัปเดต yt-dlp" ที่ header (คอลัมน์ 4), ตรวจอัตโนมัติหลังเปิดแอป 3 วินาที (`self.after(3000, self._maybe_check_ytdlp_update)`), worker ผ่าน thread + `self.after(0, ...)`, guard: ไม่ทำงานตอนมีงานกำลังรัน/เปิด setup dialog, โหมด auto เงียบเมื่อ error/ยังไม่ติดตั้ง, โหมด manual แสดง messagebox; ทำงานผ่าน job infra (`_begin_job/_set_progress/_finish_job/_cancelled`)                                                                     |
| `tests/test_ytdlp_update.py` (ใหม่) | 16 tests: version parse/compare, GitHub checksum parse, checksum verify, `os.replace` atomic, installed record, HTTPS-only, cancel, update รุ่นที่ไม่ใหม่กว่าข้าม                                                                                                                                                                                                                                                             |

### UI flow (ทำงานอย่างไร)
1. เปิดแอป → 3 วิ → `_maybe_check_ytdlp_update()` → thread เช็ค → ถ้ามีรุ่นใหม่ (และไม่ใช่ auto-silent) ถาม `askyesno` → `_start_ytdlp_update`
2. อัปเดต: ดาวน์โหลด + ตรวจ checksum + `os.replace` → แสดง `messagebox.showinfo` เมื่อเสร็จ
3. ถ้ายังไม่ได้ติดตั้ง yt-dlp เลย → แนะนำกดปุ่ม "เครื่องมือ" เพื่อติดตั้งก่อน

### เหตุผลที่ต้องระวัง (pitfall ที่เจอ)
- `zipfile.ZipFile.writestr()` กับ **arcname แบบ string** จะใส่ `time.localtime()` ลง timestamp ใน zip
  → payload ที่สร้างใน test helper (`wheel_zip`/`embed_zip` ใน `tests/test_dependencies.py`)
  **ไม่ deterministic ข้ามการเรียก** → checksum ตรงกันในรอบเดียวแต่ไม่ตรงในอีกรอบ (flaky!
  สลับไปมา เช่น colorama/packaging/anyio/lameenc) แก้โดยส่ง `zipfile.ZipInfo(name, (1980,1,1,0,0,0))`
  (ดูเพิ่มในหัวข้อ "สิ่งที่แก้ bug ระหว่างทาง")

## ไฟล์ที่แก้/เพิ่ม

| ไฟล์                                         | งาน                                                                                                                                                                                                                                                                                      |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `clipora/separator.py` (ใหม่)                | pipeline หลัก: `demucs -n htdemucs_6s --repo <dir>` offline, parse progress, workspace (`.clipora-separate-*`) + cleanup, amix ประกอบ instrumental, แปลง/บันทึกแต่ละสเต็ม, collision/overwrite                                                                                                |
| `clipora/dependencies.py`                   | `SEPARATOR_DEPENDENCIES` (32 specs แบบ pin: python-embed 3.13.14, torch 2.13.0+cpu, numpy 2.5.2, demucs 4.1.0 + deps, model `5c90dfd2-34c22ccb.th`), staging แบบ `python-embed`/`python-wheel` (แก้ `._pth` ให้เปิด site-packages), `install_separator_toolchain()`, `install_toolchains()` |
| `clipora/ui.py`                             | โหมด `stems` ใหม่ (radio), ติ๊กเลือกสเต็ม (`stem_vars`), `_start_stems_local/_url`, `_run_stems_*`, `_done_stems`, progress/phase ของสเต็ม, เรียก `_open_tool_setup(separator=True)` เมื่อยังไม่ติดตั้ง                                                                                                |
| `clipora/setup_ui.py`                       | พารามิเตอร์ `separator` ใน `ToolSetupDialog`, ใช้ `install_toolchains()`, ข้อความ welcome/summary เพิ่มตอนติดตั้ง separator                                                                                                                                                                       |
| `clipora/importer.py`                       | `import_audio_for_processing()` (โหลดเสียงลง workspace โดยยังไม่ finalize) + `cleanup_import_workspace`                                                                                                                                                                                     |
| `clipora/tools.py`                          | `CLIPORA_SEPARATOR_PYTHON` ใน `TOOL_ENVIRONMENT_VARIABLES` + `bundled_tool_directories()`                                                                                                                                                                                                |
| `scripts/check_environment.py`              | `check_separator()` (รายงานสถานะ แต่ไม่บังคับ)                                                                                                                                                                                                                                               |
| `tests/test_separator.py` (ใหม่)             | unit: command, progress parse, output paths, workspace security                                                                                                                                                                                                                          |
| `tests/test_separator_integration.py` (ใหม่) | integration: skip ถ้า `separator_installed()` ไม่จริง                                                                                                                                                                                                                                       |
| `tests/test_dependencies.py`                | staging embed/wheel, `install_separator_toolchain`, `install_toolchains`                                                                                                                                                                                                                 |
| `tests/test_check_environment.py`           | `check_separator` ด้วย mock                                                                                                                                                                                                                                                               |

## สิ่งที่แก้ bug ระหว่างทาง (สำคัญ)

1. **amix filtergraph** — คำสั่ง instrumental เดิม `amix=...` ไม่มี label + `-map 0:a:0` ทำให้ fail ด้วย
   `Cannot find an unused audio input stream...` แก้โดย label input `[0:a][1:a]...[4:a]` และ `-map [aout]`
2. **ลำดับการติดตั้ง staging** — เดิม `_replace_directory` ย้าย `python` ก่อน ทำให้ wheel ที่อยู่
   ใน `staging/python/site-packages` หาย แก้โดยเรียง destination จาก shallow → deep
   และข้าม destination ที่ ancestor ถูกแทนที่แล้ว
3. **flaky checksum ใน test_dependencies** — `writestr('name', data)` ใส่ timestamp เป็นเวลาปัจจุบัน
   ทำให้ `payload_for()` ให้ค่าไม่คงที่ → `matching_specs()` คำนวณ sha ได้ค่าหนึ่ง แต่ `fake_download`
   เขียนอีกค่าหนึ่ง (สลับไปมาระหว่างรอบ). แก้ใน test helper โดยส่ง `zipfile.ZipInfo(name, (1980,1,1,0,0,0))`
   ให้ `writestr` แทนการส่ง string

## วิธีทดสอบ

```powershell
python -m compileall -q app.py clipora tests scripts
python -m unittest discover -s tests -v
```

## งานต่อ (ยังไม่ทำ)

- [ ] **Manual GUI smoke test** — สลับโหมด audio/video/stems, ติ๊กสเต็ม, overwrite prompt,
      ปุ่มติดตั้งเมื่อยังไม่ติดตั้ง separator, ปุ่ม "อัปเดต yt-dlp" (ตอนยังไม่ติดตั้ง/ติดตั้งแล้ว/อัปเดตล่าสุด),
      ข้อความไทย, scale 100/125/150%
- [ ] ทดสอบ URL flow จริง (YouTube) ด้วย `CLIPORA_RUN_NETWORK_TESTS=1`
- [ ] ทดสอบ cancellation ระหว่างแยกสเต็ม (สร้าง test ไว้ยัง? — ยังไม่มี integration สำหรับ cancel)
- [ ] เช็ค `test_version_is_synchronized_with_packaging_metadata` ถ้าจะ bump version + เขียน release notes

## หมายเหตุ/ข้อควรรู้

- โมเดล: `htdemucs_6s` จาก
  `https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/5c90dfd2-34c22ccb.th`
  (sha256 ขึ้นต้น `34c22ccb` ตรงกับชื่อไฟล์) วางที่ `separator/models/htdemucs_6s.th`
- ใช้ `--repo <separator_models_dir>` เพื่อบังคับ offline (ไม่พึ่ง HuggingFace)
- ต้องมี **numpy** ด้วย (demucs/audio.py import numpy ตอน runtime)
- `find_separator_python()` รองรับ `CLIPORA_SEPARATOR_PYTHON` override สำหรับ dev
- `stage_bundled_tools.py` ยังใช้แค่ `WINDOWS_X64_DEPENDENCIES` — separator ไปดาวน์โหลดตอน install ไม่ bundle
- อย่าลืมว่าไฟล์บางไฟล์มี warning CRLF→LF จาก git — ปกติ ไม่กระทบ