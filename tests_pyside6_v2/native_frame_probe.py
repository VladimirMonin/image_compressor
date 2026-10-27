"""Explicit real-Windows QPA probe for the native frame owner; not an offscreen test.

Run with QT_QPA_PLATFORM=windows. Writes an owned JSON receipt; a pixel screenshot
is deliberately not a gate here (the visual direction is recorded separately).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from gui_pyside6_v2 import theme
from gui_pyside6_v2.window import MainWindow

from .conftest import pump
from .rendering import configure_test_fonts

ROOT = Path(__file__).resolve().parents[1]
CANDIDATE = ROOT / "dist/windows-pyside6/20261023-candidate-02/ImageCompressorV2.exe"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(ROOT / ".agent-work/native-frame") and not output.exists()
    output.mkdir(parents=True, exist_ok=False)
    assert not any(name.startswith("PyQt6") for name in sys.modules)
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication) and app.platformName() == "windows", app.platformName()
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    configure_test_fonts()

    window = MainWindow()
    window.show()
    pump(app, lambda: window.controller.capabilities is not None and not window.controller.busy)
    hwnd = int(window.winId())
    facts = {
        "platform": app.platformName(),
        "sys_platform": sys.platform,
        "system_color_scheme": app.styleHints().colorScheme().name,
        "screen": window.screen().name(),
        "dpr": window.devicePixelRatioF(),
        "geometry": [window.x(), window.y(), window.width(), window.height()],
        "frame_geometry": [
            window.frameGeometry().x(),
            window.frameGeometry().y(),
            window.frameGeometry().width(),
            window.frameGeometry().height(),
        ],
        "initial_hwnd": hwnd,
        "initial_theme": window.theme,
        "native_frame_supported": theme._native_frame_supported(),
        "source_theme_sha256": sha(ROOT / "gui_pyside6_v2/theme.py"),
        "candidate_exe": {
            "path": CANDIDATE.relative_to(ROOT).as_posix(),
            "sha256": sha(CANDIDATE),
            "bytes": CANDIDATE.stat().st_size,
        },
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    direct = {
        "dark": bool(theme._set_dark_frame(hwnd, True)),
        "light": bool(theme._set_dark_frame(hwnd, False)),
    }
    facts["direct_dwm_results"] = direct  # Both are HRESULT==S_OK facts, not pixels.

    recorded = []
    real_setter = theme._set_dark_frame

    def recorder(handle: int, dark: bool) -> bool:
        result = real_setter(handle, dark)
        recorded.append(
            {"hwnd": handle, "dark": dark, "result": bool(result), "winId": int(window.winId())}
        )
        return result

    switches = []
    theme._set_dark_frame = recorder
    try:
        for name, index in (("dark", 1), ("light", 0), ("dark", 1)):
            before = len(recorded)
            window.theme_combo.setCurrentIndex(index)
            app.processEvents()
            calls = recorded[before:]
            switches.append(
                {
                    "theme": name,
                    "calls": calls,
                    "window_theme": window.theme,
                    "palette_matches": window.palette().color(QPalette.ColorRole.Window)
                    == QColor(theme.colors(name)["surface/window"]),
                }
            )
    finally:
        theme._set_dark_frame = real_setter

    facts["switches"] = switches
    facts["final_hwnd"] = int(window.winId())
    facts["hwnd_stable"] = facts["final_hwnd"] == facts["initial_hwnd"]
    facts["final_theme"] = window.theme
    facts["visible_after_switches"] = window.isVisible()

    window.close()
    pump(app, lambda: not window.controller.busy)
    facts["closed"] = not window.isVisible()
    window.deleteLater()
    app.processEvents()

    switch_checks = []
    for switch in switches:
        call = switch["calls"][0] if len(switch["calls"]) == 1 else None
        switch_checks.append(
            switch["window_theme"] == switch["theme"]
            and switch["palette_matches"]
            and call is not None
            and call["result"]
            and call["dark"] == (switch["theme"] == "dark")
            and call["hwnd"] == facts["initial_hwnd"]
            and call["winId"] == facts["initial_hwnd"]
        )
    facts["switch_checks"] = switch_checks
    all_ok = (
        facts["native_frame_supported"]
        and direct == {"dark": True, "light": True}
        and facts["hwnd_stable"]
        and facts["visible_after_switches"]
        and facts["closed"]
        and len(switch_checks) == 3
        and all(switch_checks)
    )
    facts["all_ok"] = bool(all_ok)
    with (output / "receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(facts, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({key: facts[key] for key in ("platform", "dpr", "hwnd_stable", "all_ok")}))
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
