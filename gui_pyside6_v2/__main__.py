"""Separate optional entry point; never imports the legacy PyQt adapter."""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    if any(name == "PyQt6" or name.startswith("PyQt6.") for name in sys.modules):
        print(
            "Use a separate process for the PySide6 GUI (PyQt6 is already loaded).", file=sys.stderr
        )
        return 2
    if importlib.util.find_spec("PySide6") is None:
        print(
            "Optional GUI unavailable. Install: "
            'python -m pip install "image-compressor[gui-pyside6]"',
            file=sys.stderr,
        )
        return 2
    from PySide6.QtWidgets import QApplication

    from .window import MainWindow

    application = QApplication.instance() or QApplication(list(argv or sys.argv))
    if not isinstance(application, QApplication):
        print("A QApplication is required for the optional GUI.", file=sys.stderr)
        return 2
    application.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
