"""Windows offscreen does not enumerate system fonts. Load faces into this test process only.

No copying, font installation, persistent configuration or product dependency.
The normal Windows QPA plugin enumerates these system fonts itself.
"""

import os
from pathlib import Path

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QApplication


def configure_test_fonts():
    loaded = []
    if os.name == "nt" and QApplication.platformName() == "offscreen":
        root = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
        for filename in ("segoeui.ttf", "seguisb.ttf", "segoeuib.ttf"):
            path = root / filename
            if path.is_file():
                ident = QFontDatabase.addApplicationFont(str(path))
                assert ident >= 0, (
                    "The installed system font could not be loaded for offscreen tests"
                )
                loaded.extend(QFontDatabase.applicationFontFamilies(ident))
    return sorted(set(loaded))
