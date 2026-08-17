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

## เครื่องมือแยกสเต็มเสียง (Stem Separation toolchain)

ติดตั้งผ่านปุ่ม **เครื่องมือ** ในโหมดแยกสเต็มเสียง ไปยัง `%LOCALAPPDATA%\Clipora\tools\separator` โดยดาวน์โหลดผ่าน HTTPS ตรวจ SHA-256 ก่อนติดตั้งทุกไฟล์

### Embedded Python 3.13.14

- Download: https://www.python.org/ftp/python/3.13.14/python-3.13.14-embed-amd64.zip
- SHA-256: `90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907`
- Source: https://www.python.org/downloads/release/python-31314/
- License: https://docs.python.org/3/license.html

### PyTorch (CPU) 2.13.0+cpu

- Download: https://download.pytorch.org/whl/cpu/torch-2.13.0%2Bcpu-cp313-cp313-win_amd64.whl
- SHA-256: `a17ff48608634db245e17e8bb00a9558554a49aeb1e4f5fe6cd039af2a10515b`
- Source: https://github.com/pytorch/pytorch/releases
- License: https://github.com/pytorch/pytorch/blob/main/LICENSE

### demucs 4.1.0 + โมเดล htdemucs_6s

- demucs wheel: https://files.pythonhosted.org/packages/68/93/6f338f3f5c53522406dc32cd3b8a59abde20ac80d33604aa9dc8c82450e5/demucs-4.1.0-py3-none-any.whl
- demucs SHA-256: `4916a804702033ce934a6cdfa7e38dde03f7a7a6e85f41d0120eefe9e2966758`
- โมเดล htdemucs_6s: https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/5c90dfd2-34c22ccb.th
- โมเดล SHA-256: `34c22ccb381c6f9fdbf324f04e1e2fe21aaaf293f5ded163a162697ff9a02ddd`
- Source: https://github.com/facebookresearch/demucs
- License: https://github.com/facebookresearch/demucs/blob/main/LICENSE

### Dependencies ของ Demucs/PyTorch (Python wheels, ผ่าน PyPI)

ทุกไฟล์เป็น wheel จาก Python Package Index ตรวจ SHA-256 ก่อนติดตั้ง และ license/source ตามลิงก์ PyPI ของแต่ละแพ็กเกจ:

| แพ็กเกจ | เวอร์ชัน | SHA-256 | PyPI |
|---|---|---|---|
| numpy | 2.5.2 | `85aaccb24182c25df891ad0ec333585967e115269d5f1b17f2c9ae005bc96657` | https://pypi.org/project/numpy/ |
| julius | 0.2.8 | `6891235cbc355e629d839f87489bff8ca46e57a0e7cc35abb909c7a2aa538c25` | https://pypi.org/project/julius/ |
| lameenc | 1.8.4 | `7db3df4133d7b39f2f09ad684bf0a7a92c2d11117a0afc5db5cb152e48025b63` | https://pypi.org/project/lameenc/ |
| sphn | 0.2.1 | `ce0caa7858a5e41cd66fcfae7a034877512f12fbb838d3b54662020b97895569` | https://pypi.org/project/sphn/ |
| fsspec | 2026.7.0 | `b57ddbafedfaef7018c1ecab32aa200a9d7ca26b77965f64e48b70061249d279` | https://pypi.org/project/fsspec/ |
| networkx | 3.6.1 | `d47fbf302e7d9cbbb9e2555a0d267983d2aa476bac30e90dfbe5669bd57f3762` | https://pypi.org/project/networkx/ |
| setuptools | 84.0.0 | `51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670` | https://pypi.org/project/setuptools/ |
| sympy | 1.14.0 | `e091cc3e99d2141a0ba2847328f5479b05d94a6635cb96148ccb3f34671bd8f5` | https://pypi.org/project/sympy/ |
| mpmath | 1.3.0 | `a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c` | https://pypi.org/project/mpmath/ |
| typing_extensions | 4.16.0 | `481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8` | https://pypi.org/project/typing_extensions/ |
| einops | 0.8.2 | `54058201ac7087911181bfec4af6091bb59380360f069276601256a76af08193` | https://pypi.org/project/einops/ |
| filelock | 3.32.3 | `7f0ca4bcc0e181c60dbbd8aa9ab5b120ebb99e4e064e83636340056f833a1f09` | https://pypi.org/project/filelock/ |
| huggingface_hub | 1.27.0 | `7df6827c2f956c60fbaa64646e979e566db76f619dd0a9729dfb8c5a3eb4f68d` | https://pypi.org/project/huggingface_hub/ |
| click | 8.4.2 | `e6f9f66136c816745b9d65817da91d61d957fb16e02e4dcd0552553c5a197b76` | https://pypi.org/project/click/ |
| hf-xet | 1.6.0 | `fb4fadde1b2b70bf4c0c14a6dccbe7194b1c28947fefd5bbe3fed9d940676c3b` | https://pypi.org/project/hf-xet/ |
| httpx | 0.28.1 | `d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad` | https://pypi.org/project/httpx/ |
| httpcore | 1.0.9 | `2d400746a40668fc9dec9810239072b40b4484b640a8c38fd654a024c7a1bf55` | https://pypi.org/project/httpcore/ |
| h11 | 0.16.0 | `63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86` | https://pypi.org/project/h11/ |
| packaging | 26.3 | `d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c` | https://pypi.org/project/packaging/ |
| PyYAML | 6.0.3 | `79005a0d97d5ddabfeeea4cf676af11e647e41d81c9a7722a193022accdb6b7c` | https://pypi.org/project/PyYAML/ |
| tqdm | 4.70.0 | `7f585706bfddbdebf89daac705b2dfcc16890130727d3197ca62c732b4310953` | https://pypi.org/project/tqdm/ |
| anyio | 4.14.2 | `9f505dda5ac9f0c8309b5e8bd445a8c2bf7246f3ce950121e45ea15bc41d1494` | https://pypi.org/project/anyio/ |
| idna | 3.18 | `7f952cbe720b688055e3f87de14f5c3e5fdaa8bc3928985c4077ca689de849a2` | https://pypi.org/project/idna/ |
| certifi | 2026.7.22 | `62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775` | https://pypi.org/project/certifi/ |
| colorama | 0.4.6 | `4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6` | https://pypi.org/project/colorama/ |
| Jinja2 | 3.1.6 | `85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67` | https://pypi.org/project/Jinja2/ |
| MarkupSafe | 3.0.3 | `9a1abfdc021a164803f4d485104931fb8f8c1efd55bc6b748d2f5774e78b62c5` | https://pypi.org/project/MarkupSafe/ |
| safetensors | 0.8.0 | `096ec1a98435df7beb08853bb5aa9081a84f23d0adc67ed1a0a10550f608373f` | https://pypi.org/project/safetensors/ |

## การอัปเดต manifest

ผู้ดูแลต้องใช้ immutable release URL ตรวจ checksum จากผู้เผยแพร่ อัปเดตเวอร์ชัน/source/license พร้อมกัน เพิ่ม regression test และทดสอบ clean-machine ก่อน release ห้ามเปลี่ยนเป็น URL แบบ latest โดยไม่มี checksum ที่ตรงกับ asset นั้น
