"""Actual Fusion subcontrols, value room and input; no conversion/result DTO fixtures."""

import pytest
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QFontMetrics
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QStyle, QStyleOptionButton, QStyleOptionComboBox, QStyleOptionSpinBox


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_spin_targets_and_value_room(window, app, theme):
    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    window.settings.resize_check.setChecked(True)
    app.processEvents()
    for field in (window.settings.quality, window.settings.max_width, window.settings.max_height):
        window.settings.scroll_area.ensureWidgetVisible(field)
        app.processEvents()
        option = QStyleOptionSpinBox()
        field.initStyleOption(option)
        rectangles = [
            field.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, part, field)
            for part in (QStyle.SubControl.SC_SpinBoxUp, QStyle.SubControl.SC_SpinBoxDown)
        ]
        metrics = QFontMetrics(field.font())
        for rect in rectangles:
            assert rect.width() >= metrics.height() + 4, (field.objectName(), rect)
            assert rect.height() >= metrics.height(), (field.objectName(), rect)
            assert field.rect().contains(rect)
        assert not rectangles[0].intersects(rectangles[1])
        field.setValue(field.maximum())
        app.processEvents()
        editor = field.lineEdit()
        text_room = (editor.contentsRect().width() - editor.textMargins().left()
                     - editor.textMargins().right())
        assert metrics.horizontalAdvance(editor.displayText()) + 4 <= text_room


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_combo_target_and_popup(window, app, theme):
    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    for combo in (window.settings.output_format, window.theme_combo, window.locale_combo):
        app.processEvents()
        option = QStyleOptionComboBox()
        combo.initStyleOption(option)
        arrow = combo.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, option, QStyle.SubControl.SC_ComboBoxArrow, combo
        )
        text = combo.style().subControlRect(
            QStyle.ComplexControl.CC_ComboBox, option, QStyle.SubControl.SC_ComboBoxEditField, combo
        )
        assert arrow.width() >= QFontMetrics(combo.font()).height() + 4, arrow
        assert combo.rect().contains(arrow) and not text.intersects(arrow)
        assert QFontMetrics(combo.font()).horizontalAdvance(combo.currentText()) <= text.width()
        QTest.mouseClick(combo, Qt.MouseButton.LeftButton, pos=arrow.center())
        app.processEvents()
        view = combo.view()
        try:
            assert view.isVisible() and view.currentIndex().isValid()
            row = view.visualRect(view.currentIndex())
            assert row.height() >= QFontMetrics(combo.font()).height()
            from gui_pyside6_v2.theme import colors

            c = colors(window.theme)
            pixmap = view.viewport().grab()
            scale = pixmap.devicePixelRatio()
            image = pixmap.toImage().copy(
                QRect(
                    round(row.x() * scale),
                    round(row.y() * scale),
                    round(row.width() * scale),
                    round(row.height() * scale),
                )
            )
            pixels = [
                image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())
            ]
            assert pixels.count(QColor(c["accent/action"])) > len(pixels) * 0.2
            assert pixels.count(QColor(c["accent/on-action"])) >= 5
            target = (combo.currentIndex() + 1) % combo.count()
            target_rect = view.visualRect(view.model().index(target, 0))
            QTest.mouseMove(view.viewport(), target_rect.center())
            app.processEvents()
            assert view.indexAt(target_rect.center()).row() == target
            QTest.mouseClick(view.viewport(), Qt.MouseButton.LeftButton, pos=target_rect.center())
            app.processEvents()
            assert combo.currentIndex() == target  # Real popup selection, not setCurrentIndex.
        finally:
            QTest.keyClick(view, Qt.Key.Key_Escape)
            combo.hidePopup()
        assert not view.isVisible()


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_checkbox_indicator_and_label_input(window, app, theme):
    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    box = window.settings.resize_check
    window.settings.scroll_area.ensureWidgetVisible(box)
    app.processEvents()
    option = QStyleOptionButton()
    box.initStyleOption(option)
    indicator = box.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, box)
    assert indicator.width() >= QFontMetrics(box.font()).height(), indicator
    assert box.rect().contains(indicator)
    label = box.style().subElementRect(QStyle.SubElement.SE_CheckBoxContents, option, box)
    assert label.width() >= QFontMetrics(box.font()).horizontalAdvance(box.text())
    QTest.mouseClick(box, Qt.MouseButton.LeftButton, pos=label.center())
    assert box.isChecked() and window.settings.max_width.isEnabled()
    box.setFocus()
    QTest.keyClick(box, Qt.Key.Key_Space)
    assert not box.isChecked() and not window.settings.max_width.isEnabled()
    assert not window.settings.max_height.isEnabled()
    assert not window.settings.delete_original.isChecked()
    assert not window.settings.delete_original.isEnabled()
    assert (
        window.settings.delete_original.sizeHint().width()
        <= window.settings.delete_original.width()
    )


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_spin_mouse_keyboard_limits_and_disabled(window, app, theme):
    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    window.settings.resize_check.setChecked(True)
    for field in (window.settings.quality, window.settings.max_width, window.settings.max_height):
        window.settings.scroll_area.ensureWidgetVisible(field)
        app.processEvents()
        option = QStyleOptionSpinBox()
        field.initStyleOption(option)
        up, down = [
            field.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, part, field)
            for part in (QStyle.SubControl.SC_SpinBoxUp, QStyle.SubControl.SC_SpinBoxDown)
        ]
        value = field.minimum() + 2
        field.setValue(value)
        # Click near the OUTER edge, not on the glyph: the whole button is useful.
        QTest.mouseClick(
            field, Qt.MouseButton.LeftButton, pos=QPoint(up.left() + 3, up.center().y())
        )
        assert field.value() == value + 1
        QTest.mouseClick(
            field, Qt.MouseButton.LeftButton, pos=QPoint(down.left() + 3, down.center().y())
        )
        assert field.value() == value
        field.setFocus()
        QTest.keyClick(field, Qt.Key.Key_Up)
        assert field.value() == value + 1
        QTest.keyClick(field, Qt.Key.Key_Down)
        assert field.value() == value
        field.setValue(field.maximum())
        QTest.mouseClick(field, Qt.MouseButton.LeftButton, pos=up.center())
        QTest.keyClick(field, Qt.Key.Key_Up)
        assert field.value() == field.maximum()
        QTest.mouseClick(field, Qt.MouseButton.LeftButton, pos=down.center())
        assert field.value() == field.maximum() - 1
        field.setValue(field.minimum())
        QTest.mouseClick(field, Qt.MouseButton.LeftButton, pos=down.center())
        QTest.keyClick(field, Qt.Key.Key_Down)
        assert field.value() == field.minimum()
        window.settings.set_busy(True)  # Presentation state only; no operation/result fabricated.
        QTest.mouseClick(field, Qt.MouseButton.LeftButton, pos=up.center())
        QTest.keyClick(field, Qt.Key.Key_Up)
        assert field.value() == field.minimum()
        window.settings.set_busy(False)
    assert window.settings.quality_slider.value() == window.settings.quality.value()
    window.settings.quality.setFocus()
    QTest.keyClick(window.settings.quality, Qt.Key.Key_Tab)
    assert window.settings.quality_slider.hasFocus()
    QTest.keyClick(window.settings.quality_slider, Qt.Key.Key_Tab)
    assert window.settings.resize_check.hasFocus()
    QTest.keyClick(window.settings.resize_check, Qt.Key.Key_Space)
    assert not window.settings.max_width.isEnabled() and not window.settings.max_height.isEnabled()
    QTest.keyClick(window.settings.resize_check, Qt.Key.Key_Tab)
    assert window.settings.postfix.hasFocus()  # Disabled dimensions are skipped, not focus traps.


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_numeric_fields_wholly_visible_and_unclipped_at_minimum(window, app, theme):
    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    window.locale_combo.setCurrentIndex(2)  # Representative long translation.
    window.settings.resize_check.setChecked(True)
    for size in ((1120, 760), (900, 640)):
        window.resize(*size)
        app.processEvents()
        for field in (
            window.settings.quality,
            window.settings.max_width,
            window.settings.max_height,
        ):
            field.setValue(field.maximum())
            window.settings.scroll_area.ensureWidgetVisible(field)
            app.processEvents()
            viewport = window.settings.scroll_area.viewport()
            rect = QRect(field.mapTo(viewport, QPoint()), field.size())
            assert viewport.rect().contains(rect), (size, field.objectName(), rect, viewport.rect())
            editor = field.lineEdit()
            text_room = (editor.contentsRect().width() - editor.textMargins().left()
                         - editor.textMargins().right())
            text_width = QFontMetrics(editor.font()).horizontalAdvance(editor.displayText())
            assert text_width + 4 <= text_room


def indicator_pixels(box):
    option = QStyleOptionButton()
    box.initStyleOption(option)
    rect = box.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, box)
    pixmap = box.grab()
    scale = pixmap.devicePixelRatio()
    # Keep border/focus ring out of the glyph/fill discriminator.
    inner = rect.adjusted(3, 3, -3, -3)
    image = pixmap.toImage().copy(
        QRect(
            round(inner.x() * scale),
            round(inner.y() * scale),
            round(inner.width() * scale),
            round(inner.height() * scale),
        )
    )
    return [image.pixelColor(x, y) for x in range(image.width()) for y in range(image.height())]


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_checkbox_rendered_enabled_disabled_checked_focus(window, app, theme):
    from gui_pyside6_v2.theme import colors

    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    box = window.settings.resize_check
    window.settings.scroll_area.ensureWidgetVisible(box)
    app.processEvents()
    c = colors(theme)
    unchecked = indicator_pixels(box)
    assert unchecked.count(QColor(c["surface/window"])) > len(unchecked) * 0.6
    box.setFocus()
    QTest.keyClick(box, Qt.Key.Key_Space)
    app.processEvents()
    checked = indicator_pixels(box)
    assert checked.count(QColor(c["accent/action"])) > len(checked) * 0.4
    assert checked.count(QColor(c["accent/on-action"])) >= 8, (
        "A real contrasting checkmark is required"
    )
    focused = box.grab().toImage()
    assert any(
        focused.pixelColor(x, y) == QColor(c["focus/ring"])
        for x in range(focused.width())
        for y in range(focused.height())
    )
    window.settings.set_busy(True)
    app.processEvents()
    disabled_checked = indicator_pixels(box)
    assert box.isChecked() and not box.isEnabled()
    assert disabled_checked.count(QColor(c["surface/raised"])) > len(disabled_checked) * 0.4
    assert disabled_checked.count(QColor(c["text/secondary"])) >= 8
    QTest.keyClick(box, Qt.Key.Key_Space)
    assert box.isChecked()
    box.setChecked(False)  # Explicit presentation of disabled+unchecked, no fake business result.
    app.processEvents()
    disabled_unchecked = indicator_pixels(box)
    assert disabled_unchecked != disabled_checked
    assert disabled_unchecked.count(QColor(c["surface/raised"])) > len(disabled_unchecked) * 0.6
    window.settings.set_busy(False)
    assert box.isEnabled() and not box.isChecked()
    assert not window.settings.delete_original.isEnabled()


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_packaged_vector_palette_and_spin_arrow_ink(window, app, theme, tmp_path, monkeypatch):
    from pathlib import Path

    from PySide6.QtCore import QByteArray
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    from gui_pyside6_v2.theme import _control_asset, apply_theme, colors

    monkeypatch.chdir(tmp_path)  # URLs must not rely on the source cwd.
    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    apply_theme(window, theme)
    app.processEvents()
    c = colors(theme)
    for glyph in ("up", "down", "check"):
        for disabled in (False, True):
            asset = Path(_control_asset(theme, glyph, disabled))
            assert asset.is_absolute() and asset.is_file()
            renderer = QSvgRenderer(QByteArray(asset.read_bytes()))
            assert renderer.isValid()
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()
            image = pixmap.toImage()
            role = (
                "text/secondary"
                if disabled
                else ("accent/on-action" if glyph == "check" else "text/primary")
            )
            expected = QColor(c[role])
            visible = [
                (x, y) for x in range(32) for y in range(32) if image.pixelColor(x, y).alpha() > 20
            ]
            assert visible and all(2 <= x <= 29 and 2 <= y <= 29 for x, y in visible)
            assert sum(image.pixelColor(x, y) == expected for x, y in visible) >= 8
    field = window.settings.quality
    field.setValue(50)
    option = QStyleOptionSpinBox()
    field.initStyleOption(option)
    pixmap = field.grab()
    scale = pixmap.devicePixelRatio()
    for part in (QStyle.SubControl.SC_SpinBoxUp, QStyle.SubControl.SC_SpinBoxDown):
        rect = field.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, part, field)
        inner = rect.adjusted(5, 4, -5, -4)
        image = pixmap.toImage().copy(
            QRect(
                round(inner.x() * scale),
                round(inner.y() * scale),
                round(inner.width() * scale),
                round(inner.height() * scale),
            )
        )
        ink = [
            (x, y)
            for x in range(image.width())
            for y in range(image.height())
            if image.pixelColor(x, y) == QColor(c["text/primary"])
        ]
        assert len(ink) >= 8
        assert (max(x for x, _ in ink) - min(x for x, _ in ink)) / scale >= 7


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_numeric_text_has_inner_inset(window, app, theme):
    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    window.settings.resize_check.setChecked(True)
    app.processEvents()
    for field in (window.settings.quality, window.settings.max_width, window.settings.max_height):
        editor = field.lineEdit()
        inset = editor.mapTo(field, QPoint()).x() + editor.textMargins().left()
        assert inset >= 4, (field.objectName(), inset, editor.geometry())


@pytest.mark.parametrize("theme", ("light", "dark"))
def test_popup_outer_surface_matches_theme(window, app, theme):
    from gui_pyside6_v2.theme import colors

    window.theme_combo.setCurrentIndex(("light", "dark").index(theme))
    combo = window.settings.output_format
    combo.showPopup()
    app.processEvents()
    try:
        popup = combo.view().window()
        assert popup.isVisible()
        pixmap = popup.grab()
        image = pixmap.toImage()
        # The margin OUTSIDE the view must not retain a native-white patch in Dark.
        point = QPoint(image.width() // 2, round(3 * pixmap.devicePixelRatio()))
        assert image.pixelColor(point) == QColor(colors(theme)["surface/panel"])
    finally:
        combo.hidePopup()
