from pathlib import Path


project_root = Path(SPECPATH).parent
icon_path = project_root / 'assets' / 'clipora.ico'
version_path = project_root / 'packaging' / 'version_info.txt'

a = Analysis(
    [str(project_root / 'app.py')],
    pathex=[str(project_root)],
    binaries=[],
    datas=[
        (str(project_root / 'LICENSE'), '.'),
        (str(project_root / 'README.md'), '.'),
    ],
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
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Clipora',
)
