"""Minimum opt-in GUI consumer: real widgets/controller/thread/API, owned images only."""

from threading import Event

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QMessageBox

from gui_pyside6_v2.localization import Translator
from image_compressor import ErrorCode, imaging
from image_compressor import _windows_deletion as native

from .conftest import add, assert_readback, pump


def consent(monkeypatch, answer, mutate=None):
    calls = []

    def execute(dialog):
        calls.append((dialog.windowTitle(), dialog.text()))
        no = dialog.button(QMessageBox.StandardButton.No)
        yes = dialog.button(QMessageBox.StandardButton.Yes)
        assert dialog.defaultButton() is no
        assert dialog.standardButtons() == (
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        parent = dialog.parentWidget()
        assert yes.text() == parent.t("confirm_yes") and no.text() == parent.t("confirm_no")
        # Top-level QMessageBox must receive the SAME shared palette, not white-on-white in Dark.
        for role in (QPalette.ColorRole.Window, QPalette.ColorRole.WindowText):
            assert dialog.palette().color(role) == parent.palette().color(role)
        if mutate:
            mutate()
        return int(answer)

    monkeypatch.setattr(QMessageBox, "exec", execute)
    return calls


def test_no_consent_starts_no_worker(window, app, image_factory, monkeypatch):
    source = image_factory()
    before = source.read_bytes()
    c = add(app, window, [source])
    window.settings.delete_original.setChecked(True)
    calls = consent(monkeypatch, QMessageBox.StandardButton.No)
    generation = c.generation
    window.start_button.click()
    assert calls and c.worker is None and c.generation == generation
    assert c.result is None and not source.with_suffix(".webp").exists()
    assert source.read_bytes() == before


@pytest.mark.parametrize("language", ["ru", "en", "kk"])
def test_confirmed_true_real_api_and_every_start_confirmation(
    window, app, image_factory, monkeypatch, language,
):
    source = image_factory("PRIVATE_GUI_PATH/PRIVATE_GUI_NAME.png")
    c = add(app, window, [source])
    window.locale_combo.setCurrentIndex(("ru", "en", "kk").index(language))
    assert window.settings.delete_original.isEnabled()
    assert not window.settings.delete_original.isChecked()
    window.settings.delete_original.setChecked(True)
    window.theme_combo.setCurrentIndex(1)  # A destructive warning must remain readable in Dark.
    calls = consent(monkeypatch, QMessageBox.StandardButton.Yes)
    window.start_button.click()
    pump(app, lambda: not c.busy)
    result = c.result
    assert len(calls) == 1 and result.options.delete_original is True
    assert result.status == "succeeded" and result.counts.deleted == 1
    assert result.counts.succeeded == result.counts.published == 1
    assert result.items[0].source_disposition == "deleted" and not source.exists()
    assert_readback(result.items[0], expected_size=(400, 300))
    assert window.t("source_deleted") in window.details.toPlainText()
    assert window.t("retained") not in window.status_label.text()
    assert "deleted=1" in window.log.toPlainText()
    assert "PRIVATE_" not in window.log.toPlainText()
    assert window.settings.delete_original.isEnabled()
    # Even the next Start needs new consent; no automatic clean-up/retry of a prior request.
    calls = consent(monkeypatch, QMessageBox.StandardButton.No)
    generation = c.generation
    window.start_button.click()
    assert len(calls) == 1 and not c.busy and c.generation == generation and c.result is result


@pytest.mark.parametrize("mutation", ["queue", "options", "generation"])
def test_stale_yes_is_not_consent(window, app, image_factory, monkeypatch, mutation):
    source = image_factory()
    before = source.read_bytes()
    c = add(app, window, [source])
    window.settings.delete_original.setChecked(True)

    def change():
        if mutation == "queue":
            c.clear()
        elif mutation == "options":
            window.settings.quality.setValue(41)
        else:
            c.generation += 1

    calls = consent(monkeypatch, QMessageBox.StandardButton.Yes, change)
    window.start_button.click()
    assert len(calls) == 1 and not c.busy and c.result is None
    assert source.read_bytes() == before and not source.with_suffix(".webp").exists()


@pytest.mark.parametrize("outcome", ["retained", "unknown"])
def test_real_partial_and_unknown_are_not_green_full_success(
    window, app, image_factory, monkeypatch, outcome,
):
    source = image_factory()
    before = source.read_bytes()
    c = add(app, window, [source])
    window.settings.delete_original.setChecked(True)
    consent(monkeypatch, QMessageBox.StandardButton.Yes)
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
    assert window.t("retained") not in window.status_label.text()
    assert window.status_label.property("tone") == "warning"
    assert c.model.rows[0].status == "partial"
    assert window.tabs.currentIndex() == 1
    tooltip = c.model.data(c.model.index(0, 3), Qt.ItemDataRole.ToolTipRole)
    assert window.t("source_" + outcome) in tooltip
    if outcome == "retained":
        assert source.read_bytes() == before
    else:
        assert not source.exists()  # Real disposition, only its confirmation is fault-injected.


def test_true_busy_and_finished_lifetime(window, app, image_factory, monkeypatch):
    source = image_factory()
    c = add(app, window, [source])
    window.settings.delete_original.setChecked(True)
    consent(monkeypatch, QMessageBox.StandardButton.Yes)
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
        window.start()
        assert c.worker is worker
        release.set()
        pump(app, lambda: not c.busy)
        assert c.result.counts.deleted == 1 and window.settings.delete_original.isEnabled()
        assert not source.exists()
    finally:
        release.set()
        pump(app, lambda: not c.busy)


def test_localized_irreversible_warning_and_dispositions():
    for language in ("ru", "en", "kk"):
        t = Translator(language)
        warning = t("delete_confirmation", count=2, format="WEBP", quality=80,
                    bounds="1920×1080", postfix="_small")
        assert "2" in warning and "WEBP" in warning and "80" in warning and "1920×1080" in warning
        assert len(warning) > 150 and warning != "delete_confirmation"
        assert all(t("source_" + status) != "source_" + status for status in
                   ("retained", "deleted", "unknown"))
        for code in (ErrorCode.SOURCE_DELETION_FAILED, ErrorCode.SOURCE_DELETION_SKIPPED,
                     ErrorCode.SOURCE_DELETION_UNCONFIRMED):
            assert code.value in t.error(code)
