from pathlib import Path

import pytest
from PySide6.QtCore import QMimeData, QPoint, QPointF, QRect, Qt, QUrl
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QFontInfo, QFontMetrics
from PySide6.QtTest import QTest

from gui_pyside6_v2.localization import CATALOG, Translator
from gui_pyside6_v2.theme import add_icon
from gui_pyside6_v2.widgets import DropPanel
from gui_pyside6_v2.window import MainWindow
from image_compressor import ErrorCode, get_capabilities

from .conftest import add, convert, pump


def bounds(widget, ancestor):
    return QRect(widget.mapTo(ancestor, QPoint(0, 0)), widget.size())


@pytest.mark.parametrize("language", ["ru", "en", "kk"])
@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize("size", [(1120, 760), (900, 640)])
def test_geometry_language_theme_and_bounded_growth(
    window, app, image_factory, language, theme, size
):
    source = image_factory("long_synthetic_ӘҒҚҢӨҰҮҺІ_" + "x" * 90 + ".png")
    add(app, window, [source])
    window.settings.resize_check.setChecked(True)
    window.settings.postfix.setText("_unchanged")
    window.locale_combo.setCurrentIndex(("ru", "en", "kk").index(language))
    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    window.resize(*size)
    app.processEvents()
    window.layout().activate()
    app.processEvents()
    assert (window.width(), window.height()) == size
    shell = window.shell
    actions = [window.clear_button, window.stop_button, window.start_button]
    for control in [
        *actions,
        window.add_button,
        window.folder_button,
        window.settings.safety,
        window.settings.safety_explanation,
    ]:
        assert control.isVisible()
        assert shell.rect().contains(bounds(control, shell)), (
            control.objectName(),
            bounds(control, shell),
        )
    for a, b in zip(actions, actions[1:]):
        assert not bounds(a, shell).intersects(bounds(b, shell))
    for button in [*actions, window.add_button, window.folder_button]:
        icon_width = 24 if not button.icon().isNull() else 0
        assert (
            button.width()
            >= QFontMetrics(button.font()).horizontalAdvance(button.text()) + 20 + icon_width
        )
    checkbox = window.settings.delete_original
    assert checkbox.sizeHint().width() <= checkbox.width(), (
        language,
        checkbox.sizeHint(),
        checkbox.size(),
    )
    explanation = window.settings.safety_explanation
    text_height = (
        QFontMetrics(explanation.font())
        .boundingRect(
            QRect(0, 0, explanation.width(), 1000),
            int(Qt.TextFlag.TextWordWrap),
            explanation.text(),
        )
        .height()
    )
    assert text_height <= explanation.height() + 1
    assert window.controller.paths == (source,)
    assert window.settings.postfix.text() == "_unchanged"
    assert window.settings.resize_check.isChecked()
    for control in (
        window.settings.output_format,
        window.settings.postfix,
        window.settings.recursive,
    ):
        window.settings.scroll_area.ensureWidgetVisible(control)
        app.processEvents()
        viewport = window.settings.scroll_area.viewport()
        assert bounds(control, viewport).intersects(viewport.rect())
    minimum = window.minimumSize()
    for i in range(1200):
        window._append_raw_event(f"event=synthetic_tick index={i}")
    model = window.controller.model
    paths = tuple(Path(f"synthetic-{index}.png") for index in range(1000))
    model.replace_selection(paths, (None,) * len(paths))
    window._refresh()
    app.processEvents()
    assert len(window._raw_events) == 500
    assert window._raw_events[-1] == "event=synthetic_tick index=1199"
    assert window.minimumSize() == minimum
    assert window.table.verticalScrollBar().maximum() > 0
    assert shell.rect().contains(bounds(window.footer, shell))
    assert QFontInfo(window.font()).family() == "Segoe UI"
    if language == "kk":
        metrics = QFontMetrics(window.font())
        # QChar overload in this binding mis-converts non-Latin Python str;
        # use the unambiguous Unicode codepoint overload and actual face coverage.
        from PySide6.QtGui import QRawFont

        raw_font = QRawFont.fromFont(window.font())
        assert all(metrics.inFontUcs4(ord(char)) for char in "ӘҒҚҢӨҰҮҺІәғқңөұүһі")
        assert all(raw_font.supportsCharacter(ord(char)) for char in "ӘҒҚҢӨҰҮҺІәғқңөұүһі")


def test_file_folder_dialog_and_local_drop_are_wired(window, app, image_factory, monkeypatch):
    one = image_factory("one.png")
    two = image_factory("folder/two.png")
    from gui_pyside6_v2.window import QFileDialog

    monkeypatch.setattr(QFileDialog, "getOpenFileNames", lambda *args: ([str(one)], ""))
    window.add_button.click()
    pump(app, lambda: not window.controller.busy)
    assert window.controller.paths == (one,)
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: str(two.parent))
    window.folder_button.click()
    pump(app, lambda: not window.controller.busy)
    assert window.controller.paths == (one, two)
    three = image_factory("three.png")
    mime = QMimeData()
    mime.setUrls([QUrl.fromLocalFile(str(three))])
    enter = QDragEnterEvent(
        QPoint(20, 20),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.drop_panel.dragEnterEvent(enter)
    assert enter.isAccepted()
    event = QDropEvent(
        QPointF(20, 20),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.drop_panel.dropEvent(event)
    pump(app, lambda: not window.controller.busy)
    assert event.isAccepted() and window.controller.paths == (one, two, three)
    mime.setUrls([QUrl("https://example.invalid/private.png")])
    assert DropPanel.local_paths(mime) == ()
    remote = QDragEnterEvent(
        QPoint(20, 20),
        Qt.DropAction.CopyAction,
        mime,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    window.drop_panel.dragEnterEvent(remote)
    assert not remote.isAccepted()
    mime.setUrls([QUrl.fromLocalFile(str(one)), QUrl("https://example.invalid/a.png")])
    assert DropPanel.local_paths(mime) == ()


def test_keyboard_focus_space_enter_and_combo_popup(window, app, image_factory):
    source = image_factory()
    add(app, window, [source])
    window.add_button.setFocus()
    QTest.keyClick(window.add_button, Qt.Key.Key_Tab)
    assert window.folder_button.hasFocus()
    window.settings.resize_check.setFocus()
    QTest.keyClick(window.settings.resize_check, Qt.Key.Key_Space)
    assert window.settings.resize_check.isChecked() and window.settings.max_width.isEnabled()
    window.settings.output_format.setFocus()
    window.settings.output_format.showPopup()
    app.processEvents()
    popup = window.settings.output_format.view()
    assert popup.isVisible() and popup.currentIndex().isValid()
    QTest.keyClick(popup, Qt.Key.Key_Escape)
    window.start_button.setFocus()
    QTest.keyClick(window.start_button, Qt.Key.Key_Return)
    pump(app, lambda: not window.controller.busy)
    assert window.controller.result.status == "succeeded"


def test_language_theme_preserve_terminal_options_and_log(window, app, image_factory):
    add(app, window, [image_factory()])
    window.settings.quality.setValue(0)
    result = convert(app, window)
    saved_events = tuple(window._raw_events)
    for language in [1, 2, 0]:
        window.locale_combo.setCurrentIndex(language)
        window.theme_combo.setCurrentIndex(1 - language % 2)
        assert window.controller.result is result
        assert window.settings.quality.value() == 0
        assert tuple(window._raw_events) == saved_events
        assert window.details.toPlainText()
        assert window.progress.value() == 1
        assert window.start_button.isEnabled()


def test_all_catalog_keys_errors_and_unknown_size():
    assert set(CATALOG["ru"]) == set(CATALOG["en"]) == set(CATALOG["kk"])
    for language in CATALOG:
        t = Translator(language)
        assert t.size(None) == "—" and t.size(0).startswith("0")
        for code in ErrorCode:
            assert code.value in t.error(code)
        assert all(CATALOG[language].values())


def test_engine_svg_is_valid_and_not_clipped(window):
    from PySide6.QtCore import QByteArray
    from PySide6.QtSvg import QSvgRenderer

    from gui_pyside6_v2.theme import files

    svg = files("gui_pyside6_v2").joinpath("assets/add.svg").read_bytes()
    assert QSvgRenderer(QByteArray(svg)).isValid()
    icon = add_icon("dark")
    image = icon.pixmap(24, 24).toImage()
    visible = [(x, y) for x in range(24) for y in range(24) if image.pixelColor(x, y).alpha() > 20]
    assert visible
    assert min(x for x, _ in visible) >= 2 and max(x for x, _ in visible) <= 22
    assert min(y for _, y in visible) >= 2 and max(y for _, y in visible) <= 22


def test_capability_adapter_failure_retry_clears_failure(app, monkeypatch):
    import gui_pyside6_v2.workers as workers

    original = get_capabilities
    calls = 0

    def fail_once():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("PRIVATE_CAPABILITY_EXCEPTION")
        return original()

    monkeypatch.setattr(workers.api, "get_capabilities", fail_once)
    widget = MainWindow()
    widget.show()
    try:
        pump(app, lambda: widget.controller.failure is not None and not widget.controller.busy)
        assert widget.controller.failure == ErrorCode.INTERNAL_ERROR
        assert "PRIVATE_CAPABILITY_EXCEPTION" not in widget.details.toPlainText()
        widget.start_button.click()
        pump(app, lambda: widget.controller.capabilities is not None and not widget.controller.busy)
        assert widget.controller.failure is None
        assert widget.controller.state == "empty"
    finally:
        widget.close()
        pump(app, lambda: not widget.controller.busy)
        widget.deleteLater()
        app.processEvents()
