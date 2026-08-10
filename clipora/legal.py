from __future__ import annotations

from urllib.parse import quote

DMCA_EMAIL = 'dmca@ertyu.dev'

DISCLAIMER_TEXT = """คำปฏิเสธความรับผิดชอบด้านลิขสิทธิ์

Clipora เป็นเครื่องมือประมวลผลสื่อเดสก์ท็อปที่แปลงไฟล์ในเครื่องและดาวน์โหลดสื่อสาธารณะที่ได้รับอนุญาต ผู้ใช้มีหน้าที่รับผิดชอบต่อการใช้ Clipora เพียงผู้เดียว

ข้อกำหนดในการใช้งาน
- ใช้ Clipora กับเนื้อหาที่คุณเป็นเจ้าของ ได้รับอนุญาต เป็นสาธารณสมบัติ หรือมีใบอนุญาตที่เหมาะสมเท่านั้น
- ห้ามดาวน์โหลด แยกเสียง หรือแปลงเนื้อหาที่มีลิขสิทธิ์โดยไม่ได้รับอนุญาตจากเจ้าของสิทธิ์
- อย่าใช้ Clipora เพื่อข้าม DRM, paywall, login หรือ access control ใดๆ

การปฏิเสธความรับผิดชอบ
- Clipora ไม่ได้เป็นเจ้าของหรือควบคุมเนื้อหาบนเว็บไซต์ต้นทาง และไม่เกี่ยวข้องกับ YouTube หรือผู้ให้บริการวิดีโอรายอื่น
- นักพัฒนาไม่รับผิดชอบต่อการละเมิดลิขสิทธิ์ กฎหมายในภูมิภาค หรือการละเมิดเงื่อนไขการให้บริการของเว็บไซต์ต้นทางที่เกิดจากการใช้งานของคุณ
- ประมวลผลไฟล์และลิงก์ด้วยความเสี่ยงของคุณเอง เราจะไม่รับผิดชอบต่อความเสียหายใดๆ ที่เกิดจากการใช้อย่างไม่เหมาะสม

การรายงาน DMCA
- เจ้าของสิทธิ์ที่พบว่าวิดีโอของตนถูกดาวน์โหลดผ่าน Clipora สามารถยื่นรายงาน DMCA ได้จากลิงก์ "รายงานได้ที่นี่" ในหน้าหลัก
- เราจะตรวจสอบคำร้องและบล็อกวิดีโอนั้นจากการดาวน์โหลดต่อไป
"""

DMCA_NOTE = """ฟอร์มนี้จะเปิดโปรแกรมอีเมลของคุณพร้อมข้อความรายงานที่เตรียมไว้ให้แล้ว โดยไม่มีข้อมูลใดถูกส่งจากเครื่องออกไปโดยตรง

เราอาจติดต่อกลับเพื่อขอข้อมูลเพิ่มเติม หรือแจ้งผลการคัดค้าน (counter-notice) จากผู้ที่อัปโหลดวิดีโอ"""


def build_dmca_mailto(video_url: str, email: str, reason: str) -> str:
    subject = f'DMCA Report: block video {video_url}'
    body = (
        'Hello,\n\n'
        'I am the rights holder or authorized representative of the following video '
        'and request that it be blocked from further downloads:\n\n'
        f'Video URL: {video_url}\n'
        f'Rights holder email: {email}\n\n'
        'Reason:\n'
        f'{reason}\n\n'
        'Thank you.'
    )
    return 'mailto:{0}?subject={1}&body={2}'.format(
        quote(DMCA_EMAIL, safe='@'),
        quote(subject),
        quote(body),
    )
