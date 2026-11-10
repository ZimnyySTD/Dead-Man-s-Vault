# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

added_files = [
    ('DeadMansVault/Resources', 'DeadMansVault/Resources'),
    ('logo.png', '.'),
]

hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'requests',
    'b2chks',
    'b2chks.engine',
    'b2chks.packer',
    'b2chks.extractor',
    'zstandard',
    'cryptography',
]

a = Analysis(
    ['DeadMansVault/Launcher/Application/main.py'],
    pathex=['.'],
    binaries=[],
    datas=added_files,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy', 'pandas', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='DeadMansVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='DeadMansVault/Resources/logo.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='DeadMansVault',
)
