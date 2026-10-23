"""Optional GUI exports are lazy; importing finder/API never loads Qt."""

import sys
from importlib import import_module

__all__ = [
    "ImageCompressorGUI",
    "CompressionWorker",
    "DropZone",
    "QualityWidget",
    "FormatWidget",
    "FileOptionsWidget",
    "main",
]


def __getattr__(name):
    modules = {
        "ImageCompressorGUI": ".main_window",
        "CompressionWorker": ".worker",
        "DropZone": ".widgets",
        "QualityWidget": ".widgets",
        "FormatWidget": ".widgets",
        "FileOptionsWidget": ".widgets",
    }
    if name not in modules:
        raise AttributeError(name)
    return getattr(import_module(modules[name], __name__), name)


def main():
    from PyQt6.QtWidgets import QApplication

    from .main_window import ImageCompressorGUI

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = ImageCompressorGUI()
    window.show()
    sys.exit(app.exec())
