"""Opt-in GUI deletion: real checkbox activation, no modal, owned images only."""

from threading import Event

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QStyle, QStyleOptionButton

from gui_pyside6_v2.localization import Translator
from image_compressor import ErrorCode, imaging
from image_compressor import _windows_deletion as native

from .conftest import add, assert_readback, pump


def indicator_center(box):
    option = QStyleOptionButton()
    box.initStyleOption(option)
    return box.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, box).center()


def text_center(box):
    option = QStyleOptionButton()
    box.initStyleOption(option)
    return box.style().subElementRect(QStyle.SubElement.SE_CheckBoxContents, option, box).center()


def no_modal(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("A destructive consent modal must not be shown")

    monkeypatch.setattr(QMessageBox, "exec", forbidden)


def test_default_off_real_click_and_space_activate_control(window, app, monkeypatch):
    no_modal(monkeypatch)
    box = window.settings.delete_original
    assert box.isEnabled() and not box.isChecked()
    assert box.text() and box.accessibleDescription()
    QTest.mouseClick(box, Qt.MouseButton.LeftButton, pos=indicator_center(box))
    assert box.isChecked() and window.settings.options().delete_original is True
    box.setFocus()
    QTest.keyClick(box, Qt.Key.Key_Space)
    assert not box.isChecked() and window.settings.options().delete_original is False
    # Clicking the visible label text (not only the tiny indicator) must also toggle.
    QTest.mouseClick(box, Qt.MouseButton.LeftButton, pos=text_center(box))
    assert box.isChecked()


@pytest.mark.parametrize("language", ["ru", "en", "kk"])
def test_checked_real_api_deletes_only_after_verified_output(
    window, app, image_factory, monkeypatch, language,
):
    source = image_factory("PRIVATE_GUI_PATH/PRIVATE_GUI_NAME.png")
    before = source.read_bytes()
    c = add(app, window, [source])
    assert before and source.is_file()
    window.locale_combo.setCurrentIndex(("ru", "en", "kk").index(language))
    no_modal(monkeypatch)
    box = window.settings.delete_original
    QTest.mouseClick(box, Qt.MouseButton.LeftButton, pos=indicator_center(box))
    assert box.isChecked()
    window.theme_combo.setCurrentIndex(1)  # Both themes keep the same working control.
    window.start_button.click()
    pump(app, lambda: not c.busy)
    result = c.result
    assert result.options.delete_original is True
    assert result.status == "succeeded" and result.counts.deleted == 1
    assert result.counts.succeeded == result.counts.published == 1
    item = result.items[0]
    assert item.source_disposition == "deleted" and not source.exists()
    assert_readback(item, expected_size=(400, 300))
    assert window.t("source_deleted") in window.details.toPlainText()
    assert window.t("source_deleted") in window.journal_summary.toPlainText()
    raw = chr(10).join(window._raw_events)
    assert "deleted=1" in raw and "PRIVATE_" not in raw
    assert "PRIVATE_GUI_PATH" not in window.journal_summary.toPlainText()
    assert box.isEnabled() and box.isChecked()
    # The next request still requires an explicit checked control and a new snapshot.
    assert c.request_snapshot is not None and c.request_snapshot.delete_original is True


def test_unchecked_real_api_retains_source(window, app, image_factory, monkeypatch):
    source = image_factory()
    before = source.read_bytes()
    c = add(app, window, [source])
    no_modal(monkeypatch)
    window.start_button.click()
    pump(app, lambda: not c.busy)
    result = c.result
    assert result.options.delete_original is False
    assert result.items[0].source_disposition == "retained"
    assert source.read_bytes() == before
    assert result.counts.deleted == 0


@pytest.mark.parametrize("outcome", ["retained", "unknown"])
def test_real_partial_and_unknown_are_not_green_full_success(
    window, app, image_factory, monkeypatch, outcome,
):
    source = image_factory()
    before = source.read_bytes()
    c = add(app, window, [source])
    no_modal(monkeypatch)
    QTest.mouseClick(window.settings.delete_original, Qt.MouseButton.LeftButton,
                     pos=indicator_center(window.settings.delete_original))
    if outcome == "retained":
        monkeypatch.setattr(native._api().dll, "FlushFileBuffers", lambda raw: 0)
    else:
        monkeypatch.setattr(native, "_confirm_deleted", lambda *args: False)
    window.start_button.click()
    pump(app, lambda: not c.busy)
    result = c.result
    assert result.status == "partial" and result.counts.deleted == 0
    assert result.counts.succeeded == result.counts.published == 1
    assert result.items[0].source_disposition == outcome
    assert_readback(result.items[0])
    assert window.t("source_" + outcome) in window.details.toPlainText()
    assert window.status_label.property("tone") == "warning"
    assert c.model.rows[0].status == "partial"
    assert window.tabs.currentIndex() == 1
    tooltip = c.model.data(c.model.index(0, 3), Qt.ItemDataRole.ToolTipRole)
    assert window.t("source_" + outcome) in tooltip
    if outcome == "retained":
        assert source.read_bytes() == before
    else:
        assert not source.exists()  # Real disposition; only its confirmation is fault-injected.


def test_true_busy_and_finished_lifetime(window, app, image_factory, monkeypatch):
    source = image_factory()
    c = add(app, window, [source])
    no_modal(monkeypatch)
    QTest.mouseClick(window.settings.delete_original, Qt.MouseButton.LeftButton,
                     pos=indicator_center(window.settings.delete_original))
    entered, release = Event(), Event()
    encode = imaging.encode

    def paused(*args, **kwargs):
        result = encode(*args, **kwargs)
        entered.set()
        assert release.wait(10)
        return result

    monkeypatch.setattr(imaging, "encode", paused)
    try:
        window.start_button.click()
        pump(app, entered.is_set)
        worker = c.worker
        assert worker.isRunning() and not window.settings.delete_original.isEnabled()
        assert not window.start_button.isEnabled() and not window.clear_button.isEnabled()
        assert window.t("converting") in window.journal_summary.toPlainText()
        window.start()
        assert c.worker is worker
        release.set()
        pump(app, lambda: not c.busy)
        assert c.result.counts.deleted == 1 and window.settings.delete_original.isEnabled()
        assert not source.exists()
    finally:
        release.set()
        pump(app, lambda: not c.busy)


def test_unavailable_backend_is_explicit_not_silent_false(window, app, image_factory, monkeypatch):
    source = image_factory()
    before = source.read_bytes()
    c = add(app, window, [source])
    monkeypatch.setattr(native, "available", lambda: False)
    no_modal(monkeypatch)
    QTest.mouseClick(window.settings.delete_original, Qt.MouseButton.LeftButton,
                     pos=indicator_center(window.settings.delete_original))
    window.start_button.click()
    pump(app, lambda: not c.busy)
    result = c.result
    assert result.status == "rejected" and result.counts.published == 0
    assert result.errors and result.errors[0].code is ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED
    assert source.read_bytes() == before and not source.with_suffix(".webp").exists()


def test_localized_irreversible_label_and_dispositions():
    for language in ("ru", "en", "kk"):
        t = Translator(language)
        label = t("delete").lower()
        warning = t("safe").lower()
        assert label != "delete" and warning != "safe"
        assert any(word in warning for word in ("безвозврат", "permanent", "біржола"))
        assert any(word in warning for word in ("корзин", "recycle", "себет"))
        for status in ("retained", "deleted", "unknown"):
            assert t("source_" + status) != "source_" + status
