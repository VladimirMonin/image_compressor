"""Offscreen owner tests for the native frame call; real DWM is covered by the probe."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QWidget

from gui_pyside6_v2 import theme


def test_theme_switch_reaches_frame_owner(window, app, monkeypatch):
    calls: list[tuple[str, object]] = []

    def recorder(target: QWidget, name: str) -> bool:
        calls.append((name, target))
        return True

    monkeypatch.setattr(theme, "_apply_native_frame", recorder)
    assert window.theme == "light"
    window.theme_combo.setCurrentIndex(1)
    app.processEvents()
    assert [(name, target is window) for name, target in calls] == [("dark", True)]
    assert window.palette().color(QPalette.ColorRole.Window) == QColor(
        theme.colors("dark")["surface/window"]
    )
    window.theme_combo.setCurrentIndex(0)
    app.processEvents()
    assert [(name, target is window) for name, target in calls] == [
        ("dark", True),
        ("light", True),
    ]
    assert window.palette().color(QPalette.ColorRole.Window) == QColor(
        theme.colors("light")["surface/window"]
    )


def test_light_explicitly_clears_dark_frame(window, app, monkeypatch):
    monkeypatch.setattr(theme, "_native_frame_supported", lambda: True)
    calls: list[bool] = []

    def setter(hwnd: int, dark: bool) -> bool:
        calls.append(dark)
        return True

    monkeypatch.setattr(theme, "_set_dark_frame", setter)
    monkeypatch.setattr(theme, "_redraw_frame", lambda hwnd: True)
    assert theme._apply_native_frame(window, "dark") is True
    assert theme._apply_native_frame(window, "light") is True
    assert calls == [True, False]  # Light is an explicit FALSE, not a skipped call.


def test_frame_owner_ignores_children_and_unknown_theme(window, app, monkeypatch):
    monkeypatch.setattr(theme, "_native_frame_supported", lambda: True)
    calls: list[bool] = []
    monkeypatch.setattr(theme, "_set_dark_frame", lambda hwnd, dark: calls.append(dark) or True)
    child = window.settings
    assert not child.isWindow()
    assert theme._apply_native_frame(child, "dark") is False
    assert theme._apply_native_frame(window, "sepia") is False
    assert calls == []


def test_unsupported_frame_is_fail_closed(window, app, monkeypatch):
    monkeypatch.setattr(theme, "_native_frame_supported", lambda: True)
    monkeypatch.setattr(theme, "_set_dark_frame", lambda hwnd, dark: False)
    redraws: list[int] = []
    monkeypatch.setattr(theme, "_redraw_frame", lambda hwnd: redraws.append(hwnd) or True)
    assert theme._apply_native_frame(window, "dark") is False
    assert redraws == []
    assert theme.apply_theme(window, "dark") is None
    assert window.palette().color(QPalette.ColorRole.Window) == QColor(
        theme.colors("dark")["surface/window"]
    )
    assert window.styleSheet()


def test_redraw_only_for_visible_window(app, monkeypatch):
    monkeypatch.setattr(theme, "_native_frame_supported", lambda: True)
    calls: list[bool] = []
    monkeypatch.setattr(theme, "_set_dark_frame", lambda hwnd, dark: calls.append(dark) or True)
    redraws: list[int] = []
    monkeypatch.setattr(theme, "_redraw_frame", lambda hwnd: redraws.append(hwnd) or True)
    widget = QWidget()
    try:
        assert not widget.isVisible()
        assert theme._apply_native_frame(widget, "dark") is True
        assert calls == [True]
        assert redraws == []
        widget.show()
        app.processEvents()
        assert theme._apply_native_frame(widget, "dark") is True
        assert len(redraws) == 1
    finally:
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_offscreen_platform_never_calls_dwm(window, app, monkeypatch):
    assert theme._native_frame_supported() is False
    calls: list[bool] = []
    redraws: list[int] = []
    monkeypatch.setattr(theme, "_set_dark_frame", lambda hwnd, dark: calls.append(dark) or True)
    monkeypatch.setattr(theme, "_redraw_frame", lambda hwnd: redraws.append(hwnd) or True)
    window.theme_combo.setCurrentIndex(1)
    app.processEvents()
    window.theme_combo.setCurrentIndex(0)
    app.processEvents()
    assert window.theme == "light"
    assert calls == [] and redraws == []
