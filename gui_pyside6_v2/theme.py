"""Normalized FigCraft semantic tokens adapted to Widgets, not CSS renamed to QSS."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, cast

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget

TOKENS: dict[str, Any] = json.loads(files(__package__).joinpath("tokens.json").read_text("utf-8"))


def colors(name: str) -> dict[str, str]:
    return cast(dict[str, str], TOKENS["themes"][name])


def add_icon(name: str) -> QIcon:
    # The engine-exported vector is kept intact; only its monochrome tint is adapted.
    renderer = QSvgRenderer(QByteArray(files(__package__).joinpath("assets/add.svg").read_bytes()))
    pixmap = QPixmap(24, 24)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), QColor(colors(name)["accent/action"]))
    painter.end()
    return QIcon(pixmap)


def apply_theme(window: QWidget, name: str) -> None:
    c = colors(name)
    palette = QPalette()
    for role, key in (
        (QPalette.ColorRole.Window, "surface/window"),
        (QPalette.ColorRole.WindowText, "text/primary"),
        (QPalette.ColorRole.Base, "surface/panel"),
        (QPalette.ColorRole.AlternateBase, "surface/raised"),
        (QPalette.ColorRole.Text, "text/primary"),
        (QPalette.ColorRole.Button, "surface/raised"),
        (QPalette.ColorRole.ButtonText, "text/primary"),
        (QPalette.ColorRole.Highlight, "accent/action"),
        (QPalette.ColorRole.HighlightedText, "accent/on-action"),
        (QPalette.ColorRole.ToolTipBase, "surface/panel"),
        (QPalette.ColorRole.ToolTipText, "text/primary"),
        (QPalette.ColorRole.PlaceholderText, "text/secondary"),
    ):
        palette.setColor(role, QColor(c[key]))
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(c["text/secondary"])
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(c["text/secondary"])
    )
    window.setPalette(palette)
    font = QFont(str(TOKENS["typography"]["family"]))
    font.setPixelSize(int(TOKENS["typography"]["body"]))
    window.setFont(font)
    window.setStyleSheet(f"""
        QWidget {{ color: {c["text/primary"]};
            font-family: "{TOKENS["typography"]["family"]}";
            font-size: {TOKENS["typography"]["body"]}px; }}
        QMainWindow, QWidget#Shell {{ background: {c["surface/window"]}; }}
        QFrame[role="card"] {{ background: {c["surface/panel"]}; border-radius: 12px; }}
        QFrame#Safety {{ background: {c["surface/raised"]}; border-radius: 8px; }}
        QWidget#SettingsForm, QScrollArea, QScrollArea > QWidget > QWidget {{
            background: {c["surface/panel"]}; border: none;
        }}
        QLabel {{ background: transparent; }}
        QLabel[role="caption"] {{ color: {c["text/secondary"]}; font-size: 12px; }}
        QLabel#Title {{ font-size: 24px; font-weight: 600; }}
        QLabel[role="heading"] {{ font-size: 18px; font-weight: 600; }}
        QLabel[tone="success"] {{ color: {c["state/success"]}; }}
        QLabel[tone="warning"] {{ color: {c["state/warning"]}; }}
        QLabel[tone="error"] {{ color: {c["state/error"]}; }}
        QPushButton {{ background: {c["surface/raised"]}; border: 1px solid {c["border/default"]};
                       border-radius: 8px; padding: 7px 12px; min-height: 20px; }}
        QPushButton:hover:enabled {{ border-color: {c["accent/action"]}; }}
        QPushButton:pressed:enabled {{ background: {c["surface/window"]}; }}
        QPushButton#Start {{ background: {c["accent/action"]}; color: {c["accent/on-action"]};
                             border-color: {c["accent/action"]}; font-weight: 600; }}
        QPushButton#Stop {{ background: {c["surface/panel"]}; border-color: {c["state/error"]}; }}
        QPushButton:disabled, QPushButton#Start:disabled, QPushButton#Stop:disabled {{
            background: {c["surface/raised"]}; color: {c["text/secondary"]};
            border-color: {c["border/default"]};
        }}
        QPushButton:focus, QComboBox:focus, QSpinBox:focus, QLineEdit:focus,
        QCheckBox:focus, QSlider:focus, QTableView:focus, QTabBar::tab:focus {{
            border: 2px solid {c["focus/ring"]};
        }}
        QComboBox, QSpinBox, QLineEdit {{ background: {c["surface/window"]};
            border: 1px solid {c["border/default"]}; border-radius: 6px;
            padding: 5px 8px; min-height: 20px; selection-background-color: {c["accent/action"]};
            selection-color: {c["accent/on-action"]}; }}
        QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {{
            color: {c["text/secondary"]}; }}
        QComboBox QAbstractItemView {{ background: {c["surface/panel"]};
            color: {c["text/primary"]}; selection-background-color: {c["accent/action"]};
            selection-color: {c["accent/on-action"]};
            border: 1px solid {c["border/default"]}; }}
        QCheckBox {{ spacing: 8px; padding: 3px 1px; border: 2px solid transparent; }}
        QCheckBox:disabled {{ color: {c["text/secondary"]}; }}
        QSlider::groove:horizontal {{ background: {c["surface/raised"]};
            height: 6px; border-radius: 3px; }}
        QSlider::sub-page:horizontal {{ background: {c["accent/action"]}; border-radius: 3px; }}
        QSlider::handle:horizontal {{ background: {c["accent/action"]};
            border: 1px solid {c["focus/ring"]};
            width: 14px; margin: -5px 0; border-radius: 7px; }}
        QProgressBar {{ background: {c["surface/raised"]}; border: none; border-radius: 3px; }}
        QProgressBar::chunk {{ background: {c["accent/action"]}; border-radius: 3px; }}
        QTableView {{ background: {c["surface/panel"]}; gridline-color: {c["border/default"]};
            border: none; selection-background-color: {c["accent/action"]};
            selection-color: {c["accent/on-action"]}; }}
        QTableView::item {{ padding-left: 4px; padding-right: 8px; }}
        QTableView::item:selected {{ color: {c["accent/on-action"]}; }}
        QHeaderView::section {{ background: {c["surface/panel"]}; color: {c["text/secondary"]};
            border: none; border-bottom: 1px solid {c["border/default"]};
            padding: 6px; font-size: 12px; }}
        QPlainTextEdit {{ background: {c["surface/panel"]}; border: none; font-size: 12px; }}
        QTabWidget::pane {{ background: {c["surface/panel"]}; border: none; border-radius: 8px; }}
        QTabBar::tab {{ background: {c["surface/raised"]}; padding: 5px 12px;
            border: 2px solid transparent; }}
        QTabBar::tab:selected {{ background: {c["surface/panel"]};
            border-bottom-color: {c["accent/action"]}; }}
        QScrollBar:vertical {{ background: {c["surface/raised"]}; width: 12px; margin: 0; }}
        QScrollBar::handle:vertical {{ background: {c["border/default"]}; min-height: 24px;
            border-radius: 4px; margin: 2px; }}
        QScrollBar:horizontal {{ background: {c["surface/raised"]}; height: 12px; margin: 0; }}
        QScrollBar::handle:horizontal {{ background: {c["border/default"]}; min-width: 24px;
            border-radius: 4px; margin: 2px; }}
        QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
        QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
        QToolTip {{ background: {c["surface/panel"]}; color: {c["text/primary"]};
            border: 1px solid {c["border/default"]}; padding: 4px; }}
    """)
