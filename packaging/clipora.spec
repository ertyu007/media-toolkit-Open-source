from pathlib import Path


project_root = Path(SPECPATH).parent
icon_path = project_root / 'assets' / 'clipora.ico'
version_path = project_root / 'packaging' / 'version_info.txt'
manifest_path = project_root / 'packaging' / 'clipora.manifest'
donate_qr_path = project_root / 'assets' / 'donate-qr.png'

datas = [
    (str(project_root / 'LICENSE'), '.'),
    (str(project_root / 'README.md'), '.'),
]
if donate_qr_path.is_file():
    datas.append((str(donate_qr_path), '.'))

a = Analysis(
    [str(project_root / 'app.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Clipora',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(icon_path),
    version=str(version_path),
    manifest=str(manifest_path),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Clipora',
)
