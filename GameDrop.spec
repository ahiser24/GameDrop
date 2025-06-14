# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# Get the current directory of the spec file
current_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

a = Analysis(
    ['game_drop.py'],
    pathex=[],
    binaries=[],
    datas=[
        (os.path.join(current_dir, 'gamedrop/assets'), 'assets'),
        (os.path.join(current_dir, 'gamedrop'), 'gamedrop')
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtMultimedia',
        'PySide6.QtMultimediaWidgets'
    ],
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
    name='GameDrop',
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
    icon=[os.path.join(current_dir, 'gamedrop/assets/logo.png')],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GameDrop',
)
