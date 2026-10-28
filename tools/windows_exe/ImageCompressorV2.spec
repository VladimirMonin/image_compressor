# New opt-in PySide6 recipe. The legacy PyQt spec/bat are intentionally unrelated.
import importlib.util
import os
import sys
from pathlib import Path

from PyInstaller.building.api import COLLECT, EXE, PYZ
from PyInstaller.building.build_main import Analysis

HERE = Path(SPECPATH).resolve()  # noqa: F821 - supplied by the PyInstaller spec runner
ROOT = HERE.parents[1]
helper_spec = importlib.util.spec_from_file_location("ic_windows_build_recipe", HERE / "build.py")
assert helper_spec is not None and helper_spec.loader is not None
helper = importlib.util.module_from_spec(helper_spec)
sys.modules[helper_spec.name] = helper
helper_spec.loader.exec_module(helper)
mode = os.environ.get("IC_WINDOWS_EXE_MODE", "onefile")
assert mode in ("onefile", "onedir")

a = Analysis(
    [str(HERE / "frozen_entry.py")],
    pathex=[str(ROOT), str(HERE)],
    binaries=helper.native_binaries("pillow-heif") + helper.native_binaries("pillow-avif-plugin"),
    datas=[
        (str(ROOT / "gui_pyside6_v2/tokens.json"), "gui_pyside6_v2"),
        *[(str(path), "gui_pyside6_v2/assets") for path in
          sorted((ROOT / "gui_pyside6_v2/assets").glob("*.svg"))],
        (str(Path(sys.base_prefix) / "LICENSE.txt"), "licenses/CPython"),
    ] + helper.license_inputs(),
    hiddenimports=[
        "PIL._imaging", "PIL._webp", "PIL._avif", "pillow_heif", "_pillow_heif",
        "pillow_avif", "pillow_avif._avif",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PyQt6", "PyQt5", "PySide2", "tkinter", "PIL.ImageQt", "PIL.ImageTk",
        "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets", "PySide6.QtTest", "PySide6.QtPdf",
        "pytest", "tests", "tests_pyside6_v2", "tests_windows_exe", "gui",
        "classes", "gui_main",
    ],
    noarchive=False,
    optimize=0,
)
# Official hooks first; retain only Windows/SVG plugins actually used by this GUI.
# Optional virtual-keyboard/TUIO/PDF plugin engines are pruned only if PE-dependency-unreachable.
a.binaries, removed_qt = helper.minimal_qt_binaries(a.binaries)
helper.analysis_manifest(Path(os.environ["IC_EXE_ANALYSIS_RECEIPT"]),
                         a.binaries, a.datas, a.pure, removed_qt)
pyz = PYZ(a.pure)
options = dict(
    name="ImageCompressorV2", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False, disable_windowed_traceback=True,
    runtime_tmpdir=None,
)
if mode == "onefile":
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, [], **options)
else:
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, **options)
    bundle = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ImageCompressorV2")
