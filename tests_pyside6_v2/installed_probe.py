"""Run with the PySide-only Python -I, outside the repository, AFTER wheel installation.

Exercises the real `python -m gui_pyside6_v2` module via runpy/QApplication.exec,
keyboard Start, two conversions/readbacks and close; never adds source to sys.path.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
import runpy
import sys
from dataclasses import asdict
from pathlib import Path

from PIL import Image
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontInfo
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

import gui_pyside6_v2
from gui_pyside6_v2.window import MainWindow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    output = args.output.resolve()
    output.relative_to(repo)
    output.mkdir(parents=True, exist_ok=False)
    installed = Path(gui_pyside6_v2.__file__).resolve().parent
    assert "site-packages" in str(installed) and installed != repo / "gui_pyside6_v2"
    assert importlib.util.find_spec("PyQt6") is None
    source_hashes = {}
    for source in sorted((repo / "gui_pyside6_v2").rglob("*")):
        if source.is_file() and source.suffix in (".py", ".json", ".svg"):
            relative = source.relative_to(repo / "gui_pyside6_v2")
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            assert hashlib.sha256((installed / relative).read_bytes()).hexdigest() == digest
            source_hashes[relative.as_posix()] = digest
    source = output / "installed_synthetic_ӘҒҚҢӨҰҮҺІ.png"
    with Image.new("RGB", (400, 300), (19, 141, 198)) as image:
        image.save(source)
    original_bytes = source.read_bytes()
    app = QApplication([])
    errors = []
    metadata = {
        "entry": "runpy.run_module('gui_pyside6_v2', run_name='__main__')",
        "package": str(installed),
        "platform": QApplication.platformName(),
        "versions": {
            name: importlib.metadata.version(name)
            for name in ("PySide6", "Pillow", "image-compressor")
        },
        "installed_equals_source": source_hashes,
        "screens": [],
        "conversions": [],
    }
    phase = 0
    owned = []

    def capture(widget, state):
        path = output / (state + ".png")
        pixmap = widget.grab()
        assert pixmap.save(str(path))
        info = QFontInfo(widget.font())
        metadata["screens"].append(
            {
                "file": path.name,
                "state": state,
                "theme": widget.theme,
                "language": widget.language,
                "logical_size": [widget.width(), widget.height()],
                "dpr": widget.devicePixelRatioF(),
                "png_size": [pixmap.width(), pixmap.height()],
                "requested_font": widget.font().family(),
                "resolved_font": info.family(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )

    def validate(widget, expected):
        result = widget.controller.result
        assert result.status == "succeeded" and result.counts.published == 1
        item = result.items[0]
        with Image.open(item.destination) as image:
            image.load()
            assert image.format == expected and image.size == (144, 108)
        assert item.artifact.publication == "verified"
        assert hashlib.sha256(item.destination.read_bytes()).hexdigest() == item.artifact.sha256
        assert source.read_bytes() == original_bytes
        metadata["conversions"].append(
            {
                "format": expected,
                "counts": asdict(result.counts),
                "artifact_sha256": item.artifact.sha256,
            }
        )

    def tick():
        nonlocal phase
        try:
            if not owned:
                owned.extend(w for w in QApplication.topLevelWidgets() if isinstance(w, MainWindow))
                if not owned:
                    return
            widget = owned[0]
            c = widget.controller
            if phase == 0 and c.capabilities is not None and not c.busy:
                assert widget.isVisible() and widget.windowHandle().isExposed()
                widget.resize(900, 640)
                widget.theme_combo.setCurrentIndex(1)
                widget.locale_combo.setCurrentIndex(2)
                metadata["capabilities"] = asdict(c.capabilities)
                widget.add_paths((source,))
                phase = 1
            elif phase == 1 and not c.busy:
                assert c.paths == (source,)
                widget.settings.resize_check.setChecked(True)
                widget.settings.max_width.setValue(192)
                widget.settings.max_height.setValue(108)
                capture(widget, "installed-queue")
                widget.start_button.setFocus()
                QTest.keyClick(widget.start_button, Qt.Key.Key_Return)
                phase = 2
            elif phase == 2 and not c.busy:
                validate(widget, "WEBP")
                capture(widget, "installed-webp-succeeded")
                widget.settings.output_format.setCurrentIndex(0)
                widget.settings.quality.setValue(0)
                widget.start_button.click()
                phase = 3
            elif phase == 3 and not c.busy:
                validate(widget, "JPEG")
                assert c.result.options.quality == 0
                capture(widget, "installed-jpeg-succeeded")
                phase = 4
                poll.stop()
                widget.close()
        except Exception as exc:
            errors.append(type(exc).__name__)
            poll.stop()
            for widget in owned:
                widget.close()
            if not owned:
                app.quit()

    def deadline():
        errors.append("deadline")
        for widget in owned:
            widget.close()
        if not owned:
            app.quit()

    poll = QTimer()
    poll.setInterval(80)
    poll.timeout.connect(tick)
    poll.start()
    QTimer.singleShot(20000, deadline)
    code = 0
    try:
        runpy.run_module("gui_pyside6_v2", run_name="__main__")
    except SystemExit as exc:
        code = int(exc.code or 0)
    assert code == 0 and phase == 4 and not errors, (code, phase, errors)
    assert not any(name.startswith("PyQt6") for name in sys.modules)
    assert metadata["platform"] == "windows"
    (output / "manifest.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "entry_exit": code,
                "phase": phase,
                "installed_package": str(installed),
                "platform": metadata["platform"],
                "conversions": metadata["conversions"],
            }
        )
    )


if __name__ == "__main__":
    main()
