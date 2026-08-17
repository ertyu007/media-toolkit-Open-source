from __future__ import annotations

import sys
from pathlib import Path


DONATE_IMAGE_NAME = 'donate-qr.png'
DONATE_HEADING = 'สนับสนุน Clipora'
DONATE_BODY = (
    'Clipora เป็นโปรแกรมฟรี ไม่มีโฆษณา และไม่มีค่าประมวลผลบนเซิร์ฟเวอร์\n'
    'ถ้าคุณเห็นว่ามีประโยชน์ บริจาคช่วยค่าน้ำค่าไฟและค่าดูแลเครื่องมือได้ตามสะดวก\n\n'
    'สแกน QR PromptPay ด้านล่างเพื่อบริจาค'
)
DONATE_NOTE = (
    'การบริจาคเป็นไปโดยสมัครใจ ไม่เกี่ยวกับค่าบริการหรือสิทธิ์ของเนื้อหาใดๆ '
    'และไม่ให้สิทธิพิเศษใดๆ แก่ผู้บริจาค'
)


def _resource_directories() -> tuple[Path, ...]:
    directories: list[Path] = []
    bundle_root = getattr(sys, '_MEIPASS', None)
    if bundle_root:
        directories.append(Path(bundle_root))
    if getattr(sys, 'frozen', False):
        directories.append(Path(sys.executable).resolve().parent)
    directories.append(Path(__file__).resolve().parent.parent / 'assets')
    return tuple(dict.fromkeys(directories))


def donate_image_path() -> Path | None:
    for directory in _resource_directories():
        candidate = directory / DONATE_IMAGE_NAME
        if candidate.is_file():
            return candidate
    return None