"""Normalized FigCraft semantic tokens adapted to Widgets, not CSS renamed to QSS."""

from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, cast

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPalette, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QComboBox, QSpinBox, QWidget

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


def _control_asset(name: str, glyph: str, disabled: bool = False) -> str:
    """Resolve by package, never cwd; the freezer must include these SVG assets."""
    state = "-disabled" if disabled else ""
    return str(files(__package__).joinpath(f"assets/control-{glyph}{state}-{name}.svg")).replace(
        "\\", "/"
    )


def apply_theme(window: QWidget, name: str) -> None:
    c = colors(name)
    # QSS dimensions are logical Qt px, not physical display pixels. One shared
    # button channel leaves an ordinary font-height target in each half of the field.
    button_width = 2 * int(TOKENS["typography"]["body"])
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
        QSpinBox {{ padding: 5px {button_width + 8}px 5px 8px; min-height: 28px;
            min-width: {5 * int(TOKENS["typography"]["body"])}px; }}
        QSpinBox::up-button, QSpinBox::down-button {{
            subcontrol-origin: border; width: {button_width}px;
            background: {c["surface/raised"]}; border: 1px solid {c["border/default"]}; }}
        QSpinBox::up-button {{ subcontrol-position: top right;
            border-top-right-radius: 6px; }}
        QSpinBox::down-button {{ subcontrol-position: bottom right;
            border-top-width: 0; border-bottom-right-radius: 6px; }}
        QSpinBox::up-button:hover:enabled, QSpinBox::down-button:hover:enabled {{
            background: {c["surface/panel"]}; border-color: {c["accent/action"]}; }}
        QSpinBox::up-button:pressed, QSpinBox::down-button:pressed {{
            background: {c["surface/window"]}; border-color: {c["accent/action"]}; }}
        QSpinBox::up-button:disabled, QSpinBox::down-button:disabled,
        QSpinBox::up-button:off, QSpinBox::down-button:off {{
            background: {c["surface/window"]}; border-color: {c["border/default"]}; }}
        QSpinBox::up-arrow {{ image: url("{_control_asset(name, "up")}");
            width: 14px; height: 10px; }}
        QSpinBox::down-arrow {{ image: url("{_control_asset(name, "down")}");
            width: 14px; height: 10px; }}
        QSpinBox::up-arrow:disabled, QSpinBox::up-arrow:off {{
            image: url("{_control_asset(name, "up", True)}"); }}
        QSpinBox::down-arrow:disabled, QSpinBox::down-arrow:off {{
            image: url("{_control_asset(name, "down", True)}"); }}
        QComboBox:disabled, QSpinBox:disabled, QLineEdit:disabled {{
            color: {c["text/secondary"]}; }}
        QComboBox {{ padding: 5px {button_width + 8}px 5px 8px; min-height: 28px; }}
        QComboBox::drop-down {{ subcontrol-origin: padding; subcontrol-position: top right;
            width: {button_width}px; background: {c["surface/raised"]};
            border-left: 1px solid {c["border/default"]};
            border-top-right-radius: 6px; border-bottom-right-radius: 6px; }}
        QComboBox::drop-down:hover:enabled, QComboBox::drop-down:on {{
            background: {c["surface/panel"]}; border-left-color: {c["accent/action"]}; }}
        QComboBox::drop-down:disabled {{ background: {c["surface/window"]}; }}
        QComboBox::down-arrow {{ image: url("{_control_asset(name, "down")}");
            width: 14px; height: 10px; }}
        QComboBox::down-arrow:disabled {{ image: url("{_control_asset(name, "down", True)}"); }}
        QComboBox QFrame {{ background: {c["surface/panel"]};
            border: 1px solid {c["border/default"]}; }}
        QComboBox QAbstractItemView {{ background: {c["surface/panel"]};
            color: {c["text/primary"]}; selection-background-color: {c["accent/action"]};
            selection-color: {c["accent/on-action"]};
            border: 1px solid {c["border/default"]}; outline: 0; }}
        QComboBox QAbstractItemView::item {{ min-height: 22px; padding: 5px 8px; }}
        QComboBox QAbstractItemView::item:selected, QComboBox QAbstractItemView::item:hover {{
            background: {c["accent/action"]}; color: {c["accent/on-action"]}; }}
        QComboBox QAbstractItemView::item:disabled {{ color: {c["text/secondary"]}; }}
        QCheckBox {{ spacing: 8px; padding: 3px 1px; border: 2px solid transparent; }}
        /* This existing indicator has a separate buddy label, not inline text. */
        QCheckBox#DeleteUnavailable {{ spacing: 0; }}
        QCheckBox:disabled {{ color: {c["text/secondary"]}; }}
        QCheckBox::indicator {{ width: 20px; height: 20px; border-radius: 4px;
            border: 2px solid {c["text/secondary"]}; background: {c["surface/window"]}; }}
        QCheckBox::indicator:hover:enabled {{ border-color: {c["accent/action"]}; }}
        QCheckBox::indicator:pressed:enabled {{ background: {c["surface/raised"]}; }}
        QCheckBox::indicator:checked {{ background: {c["accent/action"]};
            border-color: {c["accent/action"]}; image: url("{_control_asset(name, "check")}"); }}
        QCheckBox::indicator:disabled {{ background: {c["surface/raised"]};
            border: 2px dashed {c["text/secondary"]}; }}
        QCheckBox::indicator:checked:disabled {{
            image: url("{_control_asset(name, "check", True)}"); }}
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
    # Fusion's spin-box editor geometry does not apply the field's QSS left padding.
    # Use the real editor API for a small token-owned inset, without changing values.
    inset = int(TOKENS["spacing"][0])
    for field in window.findChildren(QSpinBox):
        field.lineEdit().setTextMargins(inset, 0, inset, 0)
    # Combo popups are separate top-level windows; their native menu margins otherwise
    # keep the application palette. Explicitly propagate this SAME theme, not a second skin.
    popup_palette = QPalette(palette)
    popup_palette.setColor(QPalette.ColorRole.Window, QColor(c["surface/panel"]))
    for combo in window.findChildren(QComboBox):
        popup = combo.view().window()
        popup.setStyleSheet(window.styleSheet())
        popup.setPalette(popup_palette)
        popup.setAutoFillBackground(True)
