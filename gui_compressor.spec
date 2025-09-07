# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Image Compressor (GUI Version)

import sys
from pathlib import Path

a = Analysis(
    ['gui_main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Модули для обработки изображений
        'pillow_heif',
        'pillow_heif._pillow_heif',
        'pillow_heif.constants',
        'pillow_avif',
        'pillow_avif_plugin',
        'PIL._tkinter_finder',
        'PIL.ImageQt',
        'PIL.ImageFile',
        'PIL.Image',
        'PIL.ImageOps',
        
        # PyQt6 модули
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        
        # Многопроцессорность и потоки
        'multiprocessing',
        'multiprocessing.spawn',
        'multiprocessing.pool',
        'multiprocessing.managers',
        'multiprocessing.context',
        'queue',
        'threading',
        
        # Системные модули
        'os',
        'sys',
        'pathlib',
        'typing',
        'time',
        
        # Наши модули
        'classes',
        'gui',
        'gui.main_window',
        'gui.worker', 
        'gui.widgets',
        'gui.styles',
        'gui.utils',
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
    name='ImageCompressorGUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,  # Отключаем strip для избежания ошибок в Windows
    upx=False,    # Отключаем UPX для стабильности
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # GUI версия без консоли
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
