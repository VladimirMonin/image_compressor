# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Image Compressor (Multiprocessing Version)

import sys
from pathlib import Path

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'pillow_heif',
        'pillow_heif._pillow_heif',
        'pillow_avif',
        'PIL._tkinter_finder',
        'PIL.ImageQt',
        'multiprocessing',
        'multiprocessing.spawn',
        'multiprocessing.pool',
        'multiprocessing.process',
        'multiprocessing.util',
        'multiprocessing.managers',
        'concurrent.futures',
        'queue',
        'threading',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'scipy',
        'pandas',
        'IPython',
        'jupyter',
        'pytest',
        'unittest',
        'PyQt6',
        'PyQt5',
        'PySide2',
        'PySide6',
    ],
    noarchive=False,
    optimize=2,
)

# Удаляем дубликаты
a.datas = list({tuple(d) for d in a.datas})

pyz = PYZ(a.pure, a.zipped_data, cipher=None)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='ImageCompressorMP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
