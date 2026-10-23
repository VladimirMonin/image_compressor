"""Bounded real synthetic GUI gallery. Explicit fresh output root; no personal images.

python -m tests_pyside6_v2.gallery --output <new-project-local-directory>
Rendered coverage is recorded separately from pytest/independent acceptance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from threading import Event
from unittest.mock import patch

if "--visible" not in sys.argv:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image  # noqa: E402
from PySide6.QtGui import QFontInfo  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import gui_pyside6_v2.window as window_module  # noqa: E402
from gui_pyside6_v2.window import MainWindow  # noqa: E402
from image_compressor import get_capabilities, imaging  # noqa: E402

from .rendering import configure_test_fonts  # noqa: E402


def pump(app, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() > deadline:
            raise TimeoutError("owned GUI gallery deadline exceeded")
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()


def settle(app):
    for _ in range(12):
        app.processEvents()
        time.sleep(0.01)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--visible", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    repo = Path(__file__).resolve().parents[1]
    output.relative_to(repo)
    output.mkdir(parents=True, exist_ok=False)
    app = QApplication.instance() or QApplication([])
    app.setStyle("Fusion")
    test_fonts = configure_test_fonts()
    app.setQuitOnLastWindowClosed(False)
    manifest = {
        "renderer": QApplication.platformName(),
        "capture": "QWidget.grab / own window client area",
        "visible": args.visible,
        "offscreen_system_font_families_loaded_for_test_only": test_fonts,
        "product_module": window_module.__file__,
        "native_sha256": hashlib.sha256(
            (repo / "design/figcraft/image-compressor-v2.figcraft").read_bytes()
        ).hexdigest(),
        "source_sha256": {
            str(path.relative_to(repo)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((repo / "gui_pyside6_v2").rglob("*"))
            if path.is_file() and path.suffix in (".py", ".json", ".svg")
        },
        "screens": [],
    }

    def capture(widget, name, state, substitute=None, surface=None):
        settle(app)
        target = surface or widget
        destination = output / (name + ".png")
        pixmap = target.grab()
        assert pixmap.save(str(destination))
        info = QFontInfo(widget.font())
        manifest["screens"].append(
            {
                "file": destination.name,
                "state": state,
                "theme": widget.theme,
                "locale": widget.language,
                "surface": "combo-popup" if surface else "main-window-client",
                "logical_size": [target.width(), target.height()],
                "dpr": target.devicePixelRatioF(),
                "png_size": [pixmap.width(), pixmap.height()],
                "requested_font": widget.font().family(),
                "resolved_font": info.family(),
                "font_pixel_size": info.pixelSize(),
                "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                "real_api": True,
                "substitute": substitute,
            }
        )

    def close(widget):
        widget.close()
        pump(app, lambda: not widget.controller.busy)
        widget.deleteLater()
        app.processEvents()

    for theme_index, theme in enumerate(("light", "dark")):
        widget = MainWindow()
        widget.theme_combo.setCurrentIndex(theme_index)
        widget.show()
        c = widget.controller
        pump(app, lambda: c.capabilities is not None and not c.busy)
        sources = []
        for i, name in enumerate(
            (
                "landscape_synthetic.png",
                "portrait_ӘҒҚҢӨҰҮҺІ.jpg",
                "long_synthetic_filename_for_elision.webp",
            )
        ):
            path = output / theme / name
            path.parent.mkdir(exist_ok=True)
            with Image.new("RGB", (400, 300), (40 + i * 50, 130, 200 - i * 40)) as image:
                image.save(path)
            sources.append(path)
        before = {path: path.read_bytes() for path in sources}
        try:
            capture(widget, f"RU-{theme}-Empty", "empty")
            widget.add_paths(tuple(sources))
            pump(app, lambda: not c.busy)
            capture(widget, f"RU-{theme}-Queue", "ready")
            if theme == "light":
                widget.locale_combo.setCurrentIndex(1)
                widget.resize(900, 640)
                capture(widget, "EN-light-Queue-minimum", "ready")
                widget.locale_combo.setCurrentIndex(0)
                widget.resize(1120, 760)
            else:
                widget.locale_combo.setCurrentIndex(2)
                widget.resize(900, 640)
                capture(widget, "KK-dark-Queue-minimum", "ready")
                widget.locale_combo.setCurrentIndex(0)
                widget.resize(1120, 760)
            entered, released = Event(), Event()
            original = imaging.encode
            calls = 0

            def paused(*arguments):
                nonlocal calls
                calls += 1
                if calls == 2:
                    entered.set()
                    if not released.wait(15):
                        raise TimeoutError("gallery safety release")
                return original(*arguments)

            try:
                with patch.object(imaging, "encode", paused):
                    widget.start_button.click()
                    pump(app, entered.is_set)
                    pump(
                        app, lambda: widget.progress.maximum() == 3 and widget.progress.value() == 1
                    )
                    capture(
                        widget,
                        f"RU-{theme}-Processing",
                        "converting",
                        "test barrier before second real encode",
                    )
                    if theme == "dark":
                        # Switching presentation during real work must preserve the active snapshot.
                        snapshot = c.request_snapshot
                        widget.locale_combo.setCurrentIndex(2)
                        assert c.request_snapshot is snapshot and c.busy
                        widget.locale_combo.setCurrentIndex(0)
                    widget.stop_button.click()
                    capture(
                        widget, f"RU-{theme}-Stop-requested", "stop_requested", "same test barrier"
                    )
                    released.set()
                    pump(app, lambda: not c.busy)
            finally:
                released.set()
                pump(app, lambda: not c.busy)
            assert c.result.status == "cancelled" and c.result.counts.published == 1
            with Image.open(c.result.items[0].destination) as result_image:
                result_image.load()
                assert result_image.format == "WEBP"
            capture(widget, f"RU-{theme}-Cancelled", "cancelled")
            widget.clear_button.click()
            widget.add_paths(tuple(sources[1:]))
            pump(app, lambda: not c.busy)
            widget.start_button.click()
            pump(app, lambda: not c.busy)
            assert c.result.status == "succeeded"
            capture(widget, f"RU-{theme}-Succeeded", "succeeded")
            assert all(path.read_bytes() == content for path, content in before.items())
            widget.clear_button.click()
            good = output / theme / "partial-good.png"
            with Image.new("RGB", (80, 60), (20, 170, 90)) as image:
                image.save(good)
            bad = output / theme / "partial-bad.png"
            bad.write_bytes(b"synthetic invalid image")
            widget.add_paths((good, bad))
            pump(app, lambda: not c.busy)
            widget.start_button.click()
            pump(app, lambda: not c.busy)
            assert c.result.status == "partial"
            capture(widget, f"RU-{theme}-Partial", "partial")
            if theme == "dark":
                widget.table.selectRow(0)
                widget.settings.output_format.setFocus()
                widget.settings.output_format.showPopup()
                capture(widget, "RU-dark-Selected-popup-focus", "partial")
                popup = widget.settings.output_format.view().window()
                assert popup.isVisible()
                capture(widget, "RU-dark-Combo-popup", "partial", surface=popup)
                widget.settings.output_format.hidePopup()
        finally:
            close(widget)

    entered, released = Event(), Event()
    original = get_capabilities

    def paused_probe():
        entered.set()
        if not released.wait(15):
            raise TimeoutError("gallery probe safety release")
        return original()

    with patch("gui_pyside6_v2.workers.api.get_capabilities", paused_probe):
        widget = MainWindow()
        widget.show()
        try:
            pump(app, entered.is_set)
            capture(
                widget,
                "RU-light-Indeterminate",
                "initializing",
                "barrier before real capability query",
            )
        finally:
            released.set()
            pump(app, lambda: not widget.controller.busy)
            close(widget)
    manifest["count"] = len(manifest["screens"])
    manifest["unique_png_hashes"] = len({screen["sha256"] for screen in manifest["screens"]})
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "count": manifest["count"],
                "unique": manifest["unique_png_hashes"],
                "platform": manifest["renderer"],
                "output": str(output),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
