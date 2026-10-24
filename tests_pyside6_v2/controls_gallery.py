"""Finite control-only source gallery; real widgets, no conversion/result fixtures.

Offscreen deliberately avoids desktop/input focus. Fonts are loaded in this process
by the existing test helper; captured logical size, actual DPR and source hashes follow.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps
from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QFontInfo
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionComboBox

from gui_pyside6_v2.window import MainWindow

from .conftest import pump
from .rendering import configure_test_fonts

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def settle(app):
    for _ in range(5):
        app.processEvents()
        time.sleep(0.012)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    assert output.is_relative_to(ROOT / ".agent-work/ui-repair") and not output.exists()
    output.mkdir(parents=True, exist_ok=False)
    assert not any(name.startswith("PyQt") for name in sys.modules)
    app = QApplication.instance() or QApplication([])
    assert isinstance(app, QApplication) and app.platformName() == "offscreen"
    app.setStyle("Fusion")
    app.setQuitOnLastWindowClosed(False)
    configure_test_fonts()
    source_paths = [
        path
        for path in (ROOT / "gui_pyside6_v2").rglob("*")
        if path.is_file() and path.suffix in (".py", ".json", ".svg")
    ]
    source_paths += [Path(__file__), Path(__file__).with_name("test_controls_appearance.py")]
    manifest = {
        "kind": "source-control-presentation-only",
        "fixture": "empty real MainWindow; no conversions",
        "head": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True
        )
        .stdout.decode()
        .strip(),
        "source": {
            path.relative_to(ROOT).as_posix(): {"sha256": sha(path), "bytes": path.stat().st_size}
            for path in sorted(source_paths)
        },
        "platform": app.platformName(),
        "screens": [],
        "desktop_capture_or_input": False,
        "business_result_created": False,
    }
    widget = MainWindow()
    widget.show()
    try:
        pump(app, lambda: widget.controller.capabilities is not None and not widget.controller.busy)

        def capture(name, condition, surface=None):
            settle(app)
            target = widget if surface is None else surface
            pixmap = target.grab()
            path = output / (name + ".png")
            assert pixmap.save(str(path))
            font = QFontInfo(widget.font())
            manifest["screens"].append(
                {
                    "file": path.name,
                    "sha256": sha(path),
                    "condition": condition,
                    "theme": widget.theme,
                    "locale": widget.language,
                    "window_logical_size": [widget.width(), widget.height()],
                    "surface": "main-window-client" if surface is None else target.objectName(),
                    "logical_size": [target.width(), target.height()],
                    "png_size": [pixmap.width(), pixmap.height()],
                    "dpr": pixmap.devicePixelRatio(),
                    "requested_font": widget.font().family(),
                    "resolved_font": font.family(),
                    "quality": widget.settings.quality.value(),
                    "resize_checked": widget.settings.resize_check.isChecked(),
                    "dimensions_enabled": widget.settings.max_width.isEnabled(),
                    "recursive_checked": widget.settings.recursive.isChecked(),
                    "form_enabled": widget.settings.form.isEnabled(),
                    "deletion_enabled": widget.settings.delete_original.isEnabled(),
                }
            )

        widget.theme_combo.setCurrentIndex(1)
        widget.settings.quality.setFocus()
        capture(
            "01-ru-dark-resize-off",
            "quality active80; resize unchecked; dimensions disabled; recursive checked",
        )
        capture(
            "01-ru-dark-controls",
            "same actual SettingsPanel, readable control closeup",
            widget.settings,
        )
        widget.theme_combo.setCurrentIndex(0)
        widget.settings.resize_check.click()
        widget.settings.quality.setValue(100)
        widget.settings.recursive.click()
        widget.settings.resize_check.setFocus()
        capture(
            "02-ru-light-resize-on",
            "resize checked/focused; dimensions enabled; recursive unchecked",
        )
        capture(
            "02-ru-light-controls",
            "same actual SettingsPanel, readable control closeup",
            widget.settings,
        )
        widget.theme_combo.setCurrentIndex(1)
        widget.settings.quality.setValue(100)
        widget.settings.set_busy(True)
        capture(
            "03-ru-dark-disabled-panel",
            "presentation-only form-disabled preset; checked + unchecked disabled; "
            "NOT a conversion/busy outcome",
            widget.settings,
        )
        widget.settings.set_busy(False)
        widget.locale_combo.setCurrentIndex(2)
        widget.settings.quality.setValue(0)
        widget.settings.max_width.setValue(widget.settings.max_width.maximum())
        widget.resize(900, 640)
        widget.settings.scroll_area.ensureWidgetVisible(widget.settings.max_width)
        widget.settings.max_width.setFocus()
        capture(
            "04-kk-dark-minimum",
            "long translation; 900x640; full ten-digit width; quality at minimum; "
            "intentional vertical form scrolling",
        )
        widget.resize(1120, 760)
        widget.locale_combo.setCurrentIndex(0)
        widget.settings.quality.setValue(80)
        widget.settings.max_width.setValue(1920)
        widget.settings.scroll_area.verticalScrollBar().setValue(0)
        for tag, combo, theme_index in (
            ("05-ru-dark-format", widget.settings.output_format, 1),
            ("06-ru-light-language", widget.locale_combo, 0),
        ):
            widget.theme_combo.setCurrentIndex(theme_index)
            combo.setFocus()
            settle(app)
            option = QStyleOptionComboBox()
            combo.initStyleOption(option)
            arrow = combo.style().subControlRect(
                QStyle.ComplexControl.CC_ComboBox, option, QStyle.SubControl.SC_ComboBoxArrow, combo
            )
            QTest.mouseClick(combo, Qt.MouseButton.LeftButton, pos=arrow.center())
            settle(app)
            view = combo.view()
            assert view.isVisible()
            hover = (combo.currentIndex() + 1) % combo.count()
            hover_rect = view.visualRect(view.model().index(hover, 0))
            QTest.mouseMove(view.viewport(), hover_rect.center())
            settle(app)
            popup = view.window()
            popup.setObjectName("owned-combo-popup")
            capture(tag + "-host", "actual host; separate top-level popup captured alongside")
            capture(
                tag + "-popup",
                "OPEN actual popup; current/hover highlight; no desktop pixels",
                popup,
            )
            manifest["screens"][-1]["popup_selected_index"] = combo.currentIndex()
            manifest["screens"][-1]["popup_hover_index"] = hover
            origin = popup.mapToGlobal(QPoint()) - widget.mapToGlobal(QPoint())
            manifest["screens"][-1]["popup_offset_from_client"] = [origin.x(), origin.y()]
            combo.hidePopup()
    finally:
        widget.settings.output_format.hidePopup()
        widget.locale_combo.hidePopup()
        widget.close()
        pump(app, lambda: not widget.controller.busy)
        assert not widget.isVisible()
        widget.deleteLater()
        app.processEvents()
    manifest["owned_window_closed"] = True
    with (output / "manifest.json").open("x", encoding="utf-8") as stream:
        json.dump(manifest, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    # Contact sheet is a labelled index of owned PNGs, not an alternative screenshot.
    sheet = Image.new("RGB", (1100, 5 * 440), (232, 236, 243))
    draw = ImageDraw.Draw(sheet)
    for index, record in enumerate(manifest["screens"]):
        x, y = (index % 2) * 550, (index // 2) * 440
        draw.text((x + 8, y + 6), record["file"], fill=(20, 30, 40))
        with Image.open(output / record["file"]) as image:
            image.load()
            thumb = ImageOps.contain(image.convert("RGB"), (534, 408))
            sheet.paste(thumb, (x + 8, y + 28))
    sheet.save(output / "gallery.png")
    print(
        json.dumps(
            {
                "output": str(output),
                "screens": len(manifest["screens"]),
                "closed": True,
                "qpa": app.platformName(),
                "dpr": manifest["screens"][0]["dpr"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
