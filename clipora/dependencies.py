from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import tempfile
import threading
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Callable, Iterable
from urllib.parse import urlsplit

from .tools import executable_filename, find_executable, managed_tools_dir


ProgressCallback = Callable[[float, str], None]
DOWNLOAD_CHUNK_SIZE = 1024 * 1024
USER_AGENT = 'Clipora/0.5.1 dependency-setup'


class DependencyInstallError(RuntimeError):
    pass


class DependencyInstallCancelled(DependencyInstallError):
    pass


@dataclass(frozen=True)
class DependencySpec:
    key: str
    display_name: str
    version: str
    url: str
    sha256: str
    expected_bytes: int
    archive_type: str
    members: tuple[tuple[str, str], ...]
    source_url: str
    license_url: str

    @property
    def destination_names(self) -> tuple[str, ...]:
        return tuple(destination for _member, destination in self.members)


WINDOWS_X64_DEPENDENCIES = (
    DependencySpec(
        key='ffmpeg',
        display_name='FFmpeg Essentials',
        version='8.1.2',
        url='https://github.com/GyanD/codexffmpeg/releases/download/8.1.2/ffmpeg-8.1.2-essentials_build.zip',
        sha256='db580001caa24ac104c8cb856cd113a87b0a443f7bdf47d8c12b1d740584a2ec',
        expected_bytes=109_728_040,
        archive_type='zip',
        members=(
            ('bin/ffmpeg.exe', 'ffmpeg.exe'),
            ('bin/ffprobe.exe', 'ffprobe.exe'),
        ),
        source_url='https://github.com/FFmpeg/FFmpeg/commit/38b88335f9',
        license_url='https://ffmpeg.org/legal.html',
    ),
    DependencySpec(
        key='yt-dlp',
        display_name='yt-dlp',
        version='2026.07.04',
        url='https://github.com/yt-dlp/yt-dlp/releases/download/2026.07.04/yt-dlp.exe',
        sha256='52fe3c26dcf71fbdc85b528589020bb0b8e383155cfa81b64dd447bbe35e24b8',
        expected_bytes=18_226_085,
        archive_type='raw',
        members=(('yt-dlp.exe', 'yt-dlp.exe'),),
        source_url='https://github.com/yt-dlp/yt-dlp/tree/2026.07.04',
        license_url='https://github.com/yt-dlp/yt-dlp/blob/2026.07.04/LICENSE',
    ),
    DependencySpec(
        key='deno',
        display_name='Deno',
        version='2.8.1',
        url='https://github.com/denoland/deno/releases/download/v2.8.1/deno-x86_64-pc-windows-msvc.zip',
        sha256='5fb5bac71f609fb91ec8960fb290885aadc27eeb22f07a8eca0c3db6be38b11a',
        expected_bytes=42_032_643,
        archive_type='zip',
        members=(('deno.exe', 'deno.exe'),),
        source_url='https://github.com/denoland/deno/tree/v2.8.1',
        license_url='https://github.com/denoland/deno/blob/v2.8.1/LICENSE.md',
    ),
)

SEPARATOR_DEPENDENCIES = (
    DependencySpec(
        key='python',
        display_name='Embedded Python',
        version='3.13.14',
        url='https://www.python.org/ftp/python/3.13.14/python-3.13.14-embed-amd64.zip',
        sha256='90b4e5b9898b72d744650524bff92377c367f44bd5fbd09e3148656c080ad907',
        expected_bytes=10_964_839,
        archive_type='python-embed',
        members=(('', 'python'),),
        source_url='https://www.python.org/downloads/release/python-31314/',
        license_url='https://docs.python.org/3/license.html',
    ),
    DependencySpec(
        key='torch',
        display_name='PyTorch (CPU)',
        version='2.13.0+cpu',
        url='https://download.pytorch.org/whl/cpu/torch-2.13.0%2Bcpu-cp313-cp313-win_amd64.whl',
        sha256='a17ff48608634db245e17e8bb00a9558554a49aeb1e4f5fe6cd039af2a10515b',
        expected_bytes=121_934_105,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url='https://github.com/pytorch/pytorch/releases',
        license_url='https://github.com/pytorch/pytorch/blob/main/LICENSE',
    ),
    DependencySpec(
        key='demucs',
        display_name='demucs',
        version='4.1.0',
        url='https://files.pythonhosted.org/packages/68/93/6f338f3f5c53522406dc32cd3b8a59abde20ac80d33604aa9dc8c82450e5/demucs-4.1.0-py3-none-any.whl',
        sha256='4916a804702033ce934a6cdfa7e38dde03f7a7a6e85f41d0120eefe9e2966758',
        expected_bytes=100567,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/demucs/',
        license_url=f'https://pypi.org/project/demucs/',
    ),
    DependencySpec(
        key='julius',
        display_name='julius',
        version='0.2.8',
        url='https://files.pythonhosted.org/packages/86/43/efdb0bcb07c47826fa55857cec0deb743f74cd83b6ba5ec9e413505a72e6/julius-0.2.8-py3-none-any.whl',
        sha256='6891235cbc355e629d839f87489bff8ca46e57a0e7cc35abb909c7a2aa538c25',
        expected_bytes=21819,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/julius/',
        license_url=f'https://pypi.org/project/julius/',
    ),
    DependencySpec(
        key='lameenc',
        display_name='lameenc',
        version='1.8.4',
        url='https://files.pythonhosted.org/packages/53/aa/673a0c57d2e7ae5d800a2a43024d5ac1660ee26c114149e26a4188be93c2/lameenc-1.8.4-cp313-cp313-win_amd64.whl',
        sha256='7db3df4133d7b39f2f09ad684bf0a7a92c2d11117a0afc5db5cb152e48025b63',
        expected_bytes=153036,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/lameenc/',
        license_url=f'https://pypi.org/project/lameenc/',
    ),
    DependencySpec(
        key='sphn',
        display_name='sphn',
        version='0.2.1',
        url='https://files.pythonhosted.org/packages/c4/0b/3a52a43797fed7b16fc6fe39dc212545eb8a0872daf176ebdeedf56d07f3/sphn-0.2.1-cp313-cp313-win_amd64.whl',
        sha256='ce0caa7858a5e41cd66fcfae7a034877512f12fbb838d3b54662020b97895569',
        expected_bytes=1608163,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/sphn/',
        license_url=f'https://pypi.org/project/sphn/',
    ),
    DependencySpec(
        key='fsspec',
        display_name='fsspec',
        version='2026.7.0',
        url='https://files.pythonhosted.org/packages/fd/3c/6a2bf344106328fd04963664a60b9bb6496fc25df8e962fcdc1367285fb9/fsspec-2026.7.0-py3-none-any.whl',
        sha256='b57ddbafedfaef7018c1ecab32aa200a9d7ca26b77965f64e48b70061249d279',
        expected_bytes=206583,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/fsspec/',
        license_url=f'https://pypi.org/project/fsspec/',
    ),
    DependencySpec(
        key='networkx',
        display_name='networkx',
        version='3.6.1',
        url='https://files.pythonhosted.org/packages/9e/c9/b2622292ea83fbb4ec318f5b9ab867d0a28ab43c5717bb85b0a5f6b3b0a4/networkx-3.6.1-py3-none-any.whl',
        sha256='d47fbf302e7d9cbbb9e2555a0d267983d2aa476bac30e90dfbe5669bd57f3762',
        expected_bytes=2068504,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/networkx/',
        license_url=f'https://pypi.org/project/networkx/',
    ),
    DependencySpec(
        key='setuptools',
        display_name='setuptools',
        version='84.0.0',
        url='https://files.pythonhosted.org/packages/95/9c/c510029fc6ef33a6275cd2c5d3cecd6613dfd6aa401d57c54f1c18852ccf/setuptools-84.0.0-py3-none-any.whl',
        sha256='51a52592b3b99e102b609654876bd65f19f999935166d1352678931132b0c670',
        expected_bytes=818216,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/setuptools/',
        license_url=f'https://pypi.org/project/setuptools/',
    ),
    DependencySpec(
        key='sympy',
        display_name='sympy',
        version='1.14.0',
        url='https://files.pythonhosted.org/packages/a2/09/77d55d46fd61b4a135c444fc97158ef34a095e5681d0a6c10b75bf356191/sympy-1.14.0-py3-none-any.whl',
        sha256='e091cc3e99d2141a0ba2847328f5479b05d94a6635cb96148ccb3f34671bd8f5',
        expected_bytes=6299353,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/sympy/',
        license_url=f'https://pypi.org/project/sympy/',
    ),
    DependencySpec(
        key='mpmath',
        display_name='mpmath',
        version='1.3.0',
        url='https://files.pythonhosted.org/packages/43/e3/7d92a15f894aa0c9c4b49b8ee9ac9850d6e63b03c9c32c0367a13ae62209/mpmath-1.3.0-py3-none-any.whl',
        sha256='a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c',
        expected_bytes=536198,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/mpmath/',
        license_url=f'https://pypi.org/project/mpmath/',
    ),
    DependencySpec(
        key='typing_extensions',
        display_name='typing_extensions',
        version='4.16.0',
        url='https://files.pythonhosted.org/packages/49/d3/b8441a820a491ddfc024b0b0cf0393375b75ea13866d9c66727e54c2fc80/typing_extensions-4.16.0-py3-none-any.whl',
        sha256='481caa481374e813c1b176ada14e97f1f67a4539ce9cfeb3f350d78d6370c2e8',
        expected_bytes=45571,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/typing_extensions/',
        license_url=f'https://pypi.org/project/typing_extensions/',
    ),
    DependencySpec(
        key='einops',
        display_name='einops',
        version='0.8.2',
        url='https://files.pythonhosted.org/packages/2a/09/f8d8f8f31e4483c10a906437b4ce31bdf3d6d417b73fe33f1a8b59e34228/einops-0.8.2-py3-none-any.whl',
        sha256='54058201ac7087911181bfec4af6091bb59380360f069276601256a76af08193',
        expected_bytes=65638,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/einops/',
        license_url=f'https://pypi.org/project/einops/',
    ),
    DependencySpec(
        key='filelock',
        display_name='filelock',
        version='3.32.3',
        url='https://files.pythonhosted.org/packages/a7/8e/50f46a9c0ce8d2861a394c1347caae037ea0431d2f67d7feb151cbc4649a/filelock-3.32.3-py3-none-any.whl',
        sha256='7f0ca4bcc0e181c60dbbd8aa9ab5b120ebb99e4e064e83636340056f833a1f09',
        expected_bytes=98901,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/filelock/',
        license_url=f'https://pypi.org/project/filelock/',
    ),
    DependencySpec(
        key='huggingface_hub',
        display_name='huggingface_hub',
        version='1.27.0',
        url='https://files.pythonhosted.org/packages/de/d8/95b735e183957c1f26d94c52977f09d466d55119cbbc1558ea4975e4c216/huggingface_hub-1.27.0-py3-none-any.whl',
        sha256='7df6827c2f956c60fbaa64646e979e566db76f619dd0a9729dfb8c5a3eb4f68d',
        expected_bytes=784926,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/huggingface_hub/',
        license_url=f'https://pypi.org/project/huggingface_hub/',
    ),
    DependencySpec(
        key='click',
        display_name='click',
        version='8.4.2',
        url='https://files.pythonhosted.org/packages/fb/e2/79c688af8b210d232694e31e59da9f6ec747bae31c3f5946e4e9b98860d5/click-8.4.2-py3-none-any.whl',
        sha256='e6f9f66136c816745b9d65817da91d61d957fb16e02e4dcd0552553c5a197b76',
        expected_bytes=119243,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/click/',
        license_url=f'https://pypi.org/project/click/',
    ),
    DependencySpec(
        key='hf-xet',
        display_name='hf-xet',
        version='1.6.0',
        url='https://files.pythonhosted.org/packages/98/b7/8c59a66d15205024662f1d66968136f13893f96df1ddc5087e2e281fc95f/hf_xet-1.6.0-cp38-abi3-win_amd64.whl',
        sha256='fb4fadde1b2b70bf4c0c14a6dccbe7194b1c28947fefd5bbe3fed9d940676c3b',
        expected_bytes=4033128,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/hf-xet/',
        license_url=f'https://pypi.org/project/hf-xet/',
    ),
    DependencySpec(
        key='httpx',
        display_name='httpx',
        version='0.28.1',
        url='https://files.pythonhosted.org/packages/2a/39/e50c7c3a983047577ee07d2a9e53faf5a69493943ec3f6a384bdc792deb2/httpx-0.28.1-py3-none-any.whl',
        sha256='d909fcccc110f8c7faf814ca82a9a4d816bc5a6dbfea25d6591d6985b8ba59ad',
        expected_bytes=73517,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/httpx/',
        license_url=f'https://pypi.org/project/httpx/',
    ),
    DependencySpec(
        key='httpcore',
        display_name='httpcore',
        version='1.0.9',
        url='https://files.pythonhosted.org/packages/7e/f5/f66802a942d491edb555dd61e3a9961140fd64c90bce1eafd741609d334d/httpcore-1.0.9-py3-none-any.whl',
        sha256='2d400746a40668fc9dec9810239072b40b4484b640a8c38fd654a024c7a1bf55',
        expected_bytes=78784,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/httpcore/',
        license_url=f'https://pypi.org/project/httpcore/',
    ),
    DependencySpec(
        key='h11',
        display_name='h11',
        version='0.16.0',
        url='https://files.pythonhosted.org/packages/04/4b/29cac41a4d98d144bf5f6d33995617b185d14b22401f75ca86f384e87ff1/h11-0.16.0-py3-none-any.whl',
        sha256='63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86',
        expected_bytes=37515,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/h11/',
        license_url=f'https://pypi.org/project/h11/',
    ),
    DependencySpec(
        key='packaging',
        display_name='packaging',
        version='26.3',
        url='https://files.pythonhosted.org/packages/63/34/ba1c580383c9eada3711951fef0795c80b829a078d72188184bcab9dd527/packaging-26.3-py3-none-any.whl',
        sha256='d7193f7c8e4e93f444fde0262bf90af30e16fa0ad0ad44cb553c87339b23cd1c',
        expected_bytes=129956,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/packaging/',
        license_url=f'https://pypi.org/project/packaging/',
    ),
    DependencySpec(
        key='PyYAML',
        display_name='PyYAML',
        version='6.0.3',
        url='https://files.pythonhosted.org/packages/97/c9/39d5b874e8b28845e4ec2202b5da735d0199dbe5b8fb85f91398814a9a46/pyyaml-6.0.3-cp313-cp313-win_amd64.whl',
        sha256='79005a0d97d5ddabfeeea4cf676af11e647e41d81c9a7722a193022accdb6b7c',
        expected_bytes=154090,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/PyYAML/',
        license_url=f'https://pypi.org/project/PyYAML/',
    ),
    DependencySpec(
        key='tqdm',
        display_name='tqdm',
        version='4.70.0',
        url='https://files.pythonhosted.org/packages/f9/1c/01bfd571a64e7f270e6bab5e33777debe0edc56759233ce84f27dec92d14/tqdm-4.70.0-py3-none-any.whl',
        sha256='7f585706bfddbdebf89daac705b2dfcc16890130727d3197ca62c732b4310953',
        expected_bytes=80184,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/tqdm/',
        license_url=f'https://pypi.org/project/tqdm/',
    ),
    DependencySpec(
        key='anyio',
        display_name='anyio',
        version='4.14.2',
        url='https://files.pythonhosted.org/packages/da/35/f2287558c17e29fafc8ef3daf819bb9834061cfa43bff8014f7df7f63bdc/anyio-4.14.2-py3-none-any.whl',
        sha256='9f505dda5ac9f0c8309b5e8bd445a8c2bf7246f3ce950121e45ea15bc41d1494',
        expected_bytes=125813,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/anyio/',
        license_url=f'https://pypi.org/project/anyio/',
    ),
    DependencySpec(
        key='idna',
        display_name='idna',
        version='3.18',
        url='https://files.pythonhosted.org/packages/1e/5e/d4e9f1a599fb8e573b7b87160658329fbf28d19eac2718f51fc3def3aa5a/idna-3.18-py3-none-any.whl',
        sha256='7f952cbe720b688055e3f87de14f5c3e5fdaa8bc3928985c4077ca689de849a2',
        expected_bytes=65455,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/idna/',
        license_url=f'https://pypi.org/project/idna/',
    ),
    DependencySpec(
        key='certifi',
        display_name='certifi',
        version='2026.7.22',
        url='https://files.pythonhosted.org/packages/0b/a7/71ac2cff56fec219ed242bb11b8efb69fcc4bec75db06fb7bfe35de520e6/certifi-2026.7.22-py3-none-any.whl',
        sha256='62f22742b58a1a33014a2b6b706588a8d7e2a88ae7bd1a6ebe8c992928483775',
        expected_bytes=136983,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/certifi/',
        license_url=f'https://pypi.org/project/certifi/',
    ),
    DependencySpec(
        key='colorama',
        display_name='colorama',
        version='0.4.6',
        url='https://files.pythonhosted.org/packages/d1/d6/3965ed04c63042e047cb6a3e6ed1a63a35087b6a609aa3a15ed8ac56c221/colorama-0.4.6-py2.py3-none-any.whl',
        sha256='4f1d9991f5acc0ca119f9d443620b77f9d6b33703e51011c16baf57afb285fc6',
        expected_bytes=25335,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/colorama/',
        license_url=f'https://pypi.org/project/colorama/',
    ),
    DependencySpec(
        key='Jinja2',
        display_name='Jinja2',
        version='3.1.6',
        url='https://files.pythonhosted.org/packages/62/a1/3d680cbfd5f4b8f15abc1d571870c5fc3e594bb582bc3b64ea099db13e56/jinja2-3.1.6-py3-none-any.whl',
        sha256='85ece4451f492d0c13c5dd7c13a64681a86afae63a5f347908daf103ce6d2f67',
        expected_bytes=134899,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/Jinja2/',
        license_url=f'https://pypi.org/project/Jinja2/',
    ),
    DependencySpec(
        key='MarkupSafe',
        display_name='MarkupSafe',
        version='3.0.3',
        url='https://files.pythonhosted.org/packages/05/73/c4abe620b841b6b791f2edc248f556900667a5a1cf023a6646967ae98335/markupsafe-3.0.3-cp313-cp313-win_amd64.whl',
        sha256='9a1abfdc021a164803f4d485104931fb8f8c1efd55bc6b748d2f5774e78b62c5',
        expected_bytes=15113,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/MarkupSafe/',
        license_url=f'https://pypi.org/project/MarkupSafe/',
    ),
    DependencySpec(
        key='safetensors',
        display_name='safetensors',
        version='0.8.0',
        url='https://files.pythonhosted.org/packages/1b/6d/3fba214c1e5e0f69991677ec3bc17023f0421776975e1de0c682dca475e2/safetensors-0.8.0-cp310-abi3-win_amd64.whl',
        sha256='096ec1a98435df7beb08853bb5aa9081a84f23d0adc67ed1a0a10550f608373f',
        expected_bytes=355540,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/safetensors/',
        license_url=f'https://pypi.org/project/safetensors/',
    ),
    DependencySpec(
        key='numpy',
        display_name='numpy',
        version='2.5.2',
        url='https://files.pythonhosted.org/packages/15/20/f3489f86d81ea460b2bcdceaed094142ca6579f6be0ec527b781d39afe68/numpy-2.5.2-cp313-cp313-win_amd64.whl',
        sha256='85aaccb24182c25df891ad0ec333585967e115269d5f1b17f2c9ae005bc96657',
        expected_bytes=12460532,
        archive_type='python-wheel',
        members=(('', 'python/site-packages'),),
        source_url=f'https://pypi.org/project/numpy/',
        license_url=f'https://pypi.org/project/numpy/',
    ),
    DependencySpec(
        key='demucs-model',
        display_name='Demucs htdemucs_6s',
        version='4.1.0',
        url='https://dl.fbaipublicfiles.com/demucs/hybrid_transformer/5c90dfd2-34c22ccb.th',
        sha256='34c22ccb381c6f9fdbf324f04e1e2fe21aaaf293f5ded163a162697ff9a02ddd',
        expected_bytes=54_996_327,
        archive_type='raw',
        members=(('htdemucs_6s.th', 'models/htdemucs_6s.th'),),
        source_url='https://github.com/facebookresearch/demucs',
        license_url='https://github.com/facebookresearch/demucs/blob/main/LICENSE',
    ),
)

def windows_toolchain_supported() -> bool:
    return sys.platform == 'win32' and os.environ.get('PROCESSOR_ARCHITECTURE', '').lower() not in {'x86', 'arm', 'arm64'}


def dependency_missing(spec: DependencySpec, destination: Path | None = None) -> bool:
    root = destination or managed_tools_dir()
    return any(not (root / filename).is_file() for filename in spec.destination_names)


def dependencies_to_install(force: bool = False) -> tuple[DependencySpec, ...]:
    selected: list[DependencySpec] = []
    for spec in WINDOWS_X64_DEPENDENCIES:
        if spec.key == 'deno' and not force and find_executable('node') is not None:
            continue
        if force or dependency_missing(spec):
            selected.append(spec)
    return tuple(selected)


def verify_sha256(path: Path, expected: str) -> None:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(DOWNLOAD_CHUNK_SIZE), b''):
            digest.update(chunk)
    actual = digest.hexdigest()
    if actual.lower() != expected.lower():
        raise DependencyInstallError(
            f'checksum ไม่ตรงสำหรับ {path.name}: คาด {expected.lower()} แต่ได้ {actual.lower()}',
        )


def _check_cancelled(cancel_event: threading.Event | None) -> None:
    if cancel_event is not None and cancel_event.is_set():
        raise DependencyInstallCancelled('ยกเลิกการติดตั้งเครื่องมือแล้ว')


def _download(
    spec: DependencySpec,
    destination: Path,
    completed_before: int,
    total_expected: int,
    on_progress: ProgressCallback,
    cancel_event: threading.Event | None,
) -> None:
    if urlsplit(spec.url).scheme != 'https':
        raise DependencyInstallError(f'ปฏิเสธ URL ที่ไม่ใช่ HTTPS: {spec.url}')
    request = urllib.request.Request(spec.url, headers={'User-Agent': USER_AGENT})
    try:
        response = urllib.request.urlopen(request, timeout=45)
    except OSError as exc:
        raise DependencyInstallError(f'เชื่อมต่อเพื่อดาวน์โหลด {spec.display_name} ไม่สำเร็จ: {exc}') from exc
    with response:
        final_url = response.geturl()
        if urlsplit(final_url).scheme != 'https':
            raise DependencyInstallError('ปลายทางดาวน์โหลดไม่ได้ใช้ HTTPS')
        declared = response.headers.get('Content-Length')
        try:
            declared_size = int(declared) if declared else None
        except ValueError:
            declared_size = None
        if declared_size and declared_size > spec.expected_bytes * 2:
            raise DependencyInstallError(f'{spec.display_name} มีขนาดเกินขีดจำกัดที่กำหนด')
        downloaded = 0
        with destination.open('xb') as target:
            while True:
                _check_cancelled(cancel_event)
                chunk = response.read(DOWNLOAD_CHUNK_SIZE)
                if not chunk:
                    break
                downloaded += len(chunk)
                if downloaded > spec.expected_bytes * 2:
                    raise DependencyInstallError(f'{spec.display_name} มีขนาดเกินขีดจำกัดที่กำหนด')
                target.write(chunk)
                fraction = min((completed_before + downloaded) / max(total_expected, 1), 0.94)
                on_progress(fraction, f'กำลังดาวน์โหลด {spec.display_name}…')
            target.flush()
            os.fsync(target.fileno())
    if downloaded == 0:
        raise DependencyInstallError(f'ดาวน์โหลด {spec.display_name} ได้ไฟล์ว่าง')


def _matching_zip_member(archive: zipfile.ZipFile, suffix: str) -> zipfile.ZipInfo:
    normalized_suffix = PurePosixPath(suffix.replace('\\', '/')).as_posix().lower()
    matches = []
    for member in archive.infolist():
        normalized = PurePosixPath(member.filename.replace('\\', '/')).as_posix().lower()
        if not member.is_dir() and (normalized == normalized_suffix or normalized.endswith(f'/{normalized_suffix}')):
            matches.append(member)
    if len(matches) != 1:
        raise DependencyInstallError(
            f'archive ต้องมีไฟล์ที่ลงท้ายด้วย {suffix} จำนวนหนึ่งไฟล์ แต่พบ {len(matches)}',
        )
    member = matches[0]
    if member.file_size <= 0 or member.file_size > 400 * 1024 * 1024:
        raise DependencyInstallError(f'ขนาดไฟล์ {member.filename} ใน archive ไม่ปลอดภัย')
    return member


def stage_dependency(spec: DependencySpec, archive_path: Path, staging: Path) -> None:
    if spec.archive_type == 'raw':
        if len(spec.members) != 1:
            raise DependencyInstallError('raw dependency ต้องมีไฟล์ปลายทางหนึ่งไฟล์')
        destination = staging / spec.members[0][1]
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(archive_path, destination)
        return
    if spec.archive_type == 'python-embed':
        destination = staging / spec.members[0][1]
        destination.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(destination)
        except (OSError, zipfile.BadZipFile) as exc:
            raise DependencyInstallError(f'แตกไฟล์ {spec.display_name} ไม่สำเร็จ: {exc}') from exc
        pth_files = list(destination.glob('python3*._pth'))
        if len(pth_files) != 1:
            raise DependencyInstallError('ไม่พบไฟล์ ._pth ใน Embedded Python')
        pth = pth_files[0]
        lines = [
            line
            for line in pth.read_text(encoding='utf-8').splitlines()
            if line.strip() not in {'site-packages', 'import site'}
        ]
        if 'site-packages' not in lines:
            lines.append('site-packages')
        if 'import site' not in lines:
            lines.append('import site')
        pth.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return
    if spec.archive_type == 'python-wheel':
        destination = staging / spec.members[0][1]
        destination.mkdir(parents=True, exist_ok=True)
        try:
            with zipfile.ZipFile(archive_path) as archive:
                archive.extractall(destination)
        except (OSError, zipfile.BadZipFile) as exc:
            raise DependencyInstallError(f'แตกไฟล์ {spec.display_name} ไม่สำเร็จ: {exc}') from exc
        return
    if spec.archive_type != 'zip':
        raise DependencyInstallError(f'ไม่รองรับ archive type: {spec.archive_type}')
    try:
        with zipfile.ZipFile(archive_path) as archive:
            for suffix, destination_name in spec.members:
                member = _matching_zip_member(archive, suffix)
                destination = staging / destination_name
                with archive.open(member) as source, destination.open('xb') as target:
                    shutil.copyfileobj(source, target, length=DOWNLOAD_CHUNK_SIZE)
    except (OSError, zipfile.BadZipFile) as exc:
        raise DependencyInstallError(f'แตกไฟล์ {spec.display_name} ไม่สำเร็จ: {exc}') from exc


def _write_install_record(root: Path, installed: Iterable[DependencySpec]) -> None:
    dependencies = {}
    existing = root / 'installed.json'
    if existing.is_file():
        try:
            previous = json.loads(existing.read_text(encoding='utf-8'))
            if previous.get('schema') == 1 and isinstance(previous.get('dependencies'), dict):
                dependencies.update(previous['dependencies'])
        except (OSError, json.JSONDecodeError, AttributeError):
            pass
    dependencies.update(
        {
            spec.key: {
                'version': spec.version,
                'sha256': spec.sha256,
                'source': spec.source_url,
                'license': spec.license_url,
            }
            for spec in installed
        }
    )
    record = {
        'schema': 1,
        'dependencies': dependencies,
    }
    temporary = root / '.installed.json.tmp'
    temporary.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(root / 'installed.json')


def install_windows_toolchain(
    on_progress: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    force: bool = False,
    destination: Path | None = None,
    specs: tuple[DependencySpec, ...] | None = None,
) -> tuple[DependencySpec, ...]:
    if specs is None and not windows_toolchain_supported():
        raise DependencyInstallError('ตัวติดตั้งอัตโนมัติรองรับ Windows x64 เท่านั้น')
    callback = on_progress or (lambda _fraction, _message: None)
    root = destination or managed_tools_dir()
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    selected = specs if specs is not None else dependencies_to_install(force=force)
    if not selected:
        callback(1.0, 'เครื่องมือพร้อมใช้งานแล้ว')
        return ()
    total_expected = sum(spec.expected_bytes for spec in selected)
    completed = 0
    installed: list[DependencySpec] = []
    with tempfile.TemporaryDirectory(prefix='.clipora-setup-', dir=str(root.parent)) as temporary_directory:
        temporary_root = Path(temporary_directory)
        staging = temporary_root / 'staging'
        staging.mkdir()
        for index, spec in enumerate(selected):
            _check_cancelled(cancel_event)
            archive_path = temporary_root / f'{index}-{spec.key}.download'
            _download(spec, archive_path, completed, total_expected, callback, cancel_event)
            callback(min((completed + spec.expected_bytes) / total_expected, 0.95), f'กำลังตรวจสอบ {spec.display_name}…')
            verify_sha256(archive_path, spec.sha256)
            stage_dependency(spec, archive_path, staging)
            completed += spec.expected_bytes
            installed.append(spec)
        _check_cancelled(cancel_event)
        callback(0.97, 'กำลังติดตั้งเครื่องมือ…')
        for spec in installed:
            for destination_name in spec.destination_names:
                staged = staging / destination_name
                if not staged.is_file() or staged.stat().st_size == 0:
                    raise DependencyInstallError(f'ไม่พบไฟล์ที่เตรียมไว้: {destination_name}')
                os.replace(staged, root / executable_filename(destination_name))
        _write_install_record(root, installed)
    callback(1.0, 'ติดตั้งเครื่องมือเรียบร้อย')
    return tuple(installed)


def _replace_directory(staged: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = target.with_name(f'.{target.name}.clipora-old')
    if backup.exists():
        shutil.rmtree(backup)
    moved = False
    if target.exists():
        os.replace(target, backup)
        moved = True
    try:
        os.replace(staged, target)
    except OSError:
        if moved and not target.exists():
            try:
                os.replace(backup, target)
            except OSError:
                pass
        raise
    if moved and backup.exists():
        shutil.rmtree(backup)


def _verify_separator_install(root: Path) -> None:
    python_exe = root / 'python' / 'python.exe'
    demucs_package = root / 'python' / 'site-packages' / 'demucs'
    model = root / 'models' / 'htdemucs_6s.th'
    if not python_exe.is_file():
        raise DependencyInstallError('ไม่พบ python.exe หลังจากติดตั้งเครื่องมือแยกสเต็ม')
    if not demucs_package.is_dir():
        raise DependencyInstallError('ไม่พบแพ็กเกจ demucs หลังจากติดตั้งเครื่องมือแยกสเต็ม')
    if not model.is_file():
        raise DependencyInstallError('ไม่พบโมเดลแยกสเต็มหลังจากติดตั้ง')


def install_separator_toolchain(
    on_progress: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    destination: Path | None = None,
    specs: tuple[DependencySpec, ...] | None = None,
) -> tuple[DependencySpec, ...]:
    callback = on_progress or (lambda _fraction, _message: None)
    root = (destination or managed_tools_dir()) / 'separator'
    root.parent.mkdir(parents=True, exist_ok=True)
    root.mkdir(parents=True, exist_ok=True)
    selected = specs if specs is not None else SEPARATOR_DEPENDENCIES
    total_expected = sum(spec.expected_bytes for spec in selected)
    completed = 0
    installed: list[DependencySpec] = []
    with tempfile.TemporaryDirectory(
        prefix='.clipora-separator-',
        dir=str(root.parent),
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)
        staging = temporary_root / 'staging'
        staging.mkdir()
        for index, spec in enumerate(selected):
            _check_cancelled(cancel_event)
            archive_path = temporary_root / f'{index}-{spec.key}.download'
            _download(spec, archive_path, completed, total_expected, callback, cancel_event)
            callback(
                min((completed + spec.expected_bytes) / total_expected, 0.94),
                f'กำลังตรวจสอบ {spec.display_name}…',
            )
            verify_sha256(archive_path, spec.sha256)
            stage_dependency(spec, archive_path, staging)
            completed += spec.expected_bytes
            installed.append(spec)
        _check_cancelled(cancel_event)
        callback(0.96, 'กำลังติดตั้งเครื่องมือแยกสเต็ม…')
        replacements: list[tuple[Path, Path]] = []
        for spec in installed:
            for destination_name in spec.destination_names:
                staged = staging / destination_name
                if not staged.exists():
                    raise DependencyInstallError(f'ไม่พบไฟล์ที่เตรียมไว้: {destination_name}')
                replacements.append((staged, root / destination_name))
        replacements.sort(key=lambda pair: len(pair[1].parts))
        handled_targets: list[Path] = []
        for staged, target in replacements:
            if any(target == handled or handled in target.parents for handled in handled_targets):
                continue
            _replace_directory(staged, target)
            handled_targets.append(target)
        _verify_separator_install(root)
        _write_install_record(root, installed)
    callback(1.0, 'ติดตั้งเครื่องมือแยกสเต็มเรียบร้อย')
    return tuple(installed)


def install_toolchains(
    on_progress: ProgressCallback | None = None,
    cancel_event: threading.Event | None = None,
    force: bool = False,
    destination: Path | None = None,
    include_separator: bool = False,
) -> tuple[DependencySpec, ...]:
    main_installed = install_windows_toolchain(
        on_progress=on_progress,
        cancel_event=cancel_event,
        force=force,
        destination=destination,
    )
    if not include_separator:
        return main_installed
    separator_installed = install_separator_toolchain(
        on_progress=on_progress,
        cancel_event=cancel_event,
        destination=destination,
    )
    return main_installed + separator_installed
