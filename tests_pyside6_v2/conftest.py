import os
import sys
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
assert not any(name.startswith("PyQt6") for name in sys.modules)

import pytest  # noqa: E402
from PIL import Image  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from gui_pyside6_v2.window import MainWindow  # noqa: E402

from .rendering import configure_test_fonts  # noqa: E402


def pump(app, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "Qt event deadline exceeded"
        app.processEvents()
        time.sleep(0.004)
    app.processEvents()


@pytest.fixture(scope="session")
def app():
    application = QApplication.instance() or QApplication([])
    application.setStyle("Fusion")
    configure_test_fonts()
    application.setQuitOnLastWindowClosed(False)
    yield application
    application.processEvents()


@pytest.fixture
def image_factory(tmp_path):
    def create(name="source.png", size=(400, 300), color=(38, 139, 201)):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with Image.new("RGB", size, color) as image:
            image.save(path)
        return path

    return create


@pytest.fixture
def window(app):
    widget = MainWindow()
    widget.show()
    pump(app, lambda: widget.controller.capabilities is not None and not widget.controller.busy)
    try:
        yield widget
    finally:
        widget.close()
        pump(app, lambda: not widget.controller.busy, timeout=20)
        widget.deleteLater()
        app.processEvents()


def add(app, window, paths):
    window.add_paths(tuple(Path(path) for path in paths))
    pump(app, lambda: not window.controller.busy)
    return window.controller


def convert(app, window):
    assert window.start_button.isEnabled()
    window.start_button.click()
    pump(app, lambda: not window.controller.busy)
    assert window.controller.result is not None
    return window.controller.result


def assert_readback(item, expected_format="WEBP", expected_size=None):
    import hashlib

    assert item.artifact is not None and item.destination.exists()
    with Image.open(item.destination) as image:
        image.load()
        assert image.format == expected_format
        if expected_size:
            assert image.size == expected_size
    artifact = item.artifact
    assert artifact.publication == "verified"
    assert artifact.size_bytes == item.destination.stat().st_size
    assert artifact.sha256 == hashlib.sha256(item.destination.read_bytes()).hexdigest()
