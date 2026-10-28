"""Journal: human summary only; all technical facts in the existing Details tab."""

from pathlib import Path
from threading import Event

import pytest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QMessageBox, QPlainTextEdit, QStyle, QStyleOptionButton

from image_compressor import Artifact, ItemResult, imaging

from .conftest import add, convert, pump


def click_checkbox(box):
    option = QStyleOptionButton()
    box.initStyleOption(option)
    rect = box.style().subElementRect(QStyle.SubElement.SE_CheckBoxIndicator, option, box)
    QTest.mouseClick(box, Qt.MouseButton.LeftButton, pos=rect.center())


def test_summary_is_human_only_and_details_hold_technical_facts(window, app, image_factory):
    source = image_factory()
    c = add(app, window, [source])
    convert(app, window)
    item = c.result.items[0]
    artifact = item.artifact
    assert artifact is not None and artifact.publication == "verified"
    summary = window.journal_summary.toPlainText()
    details = window.details.toPlainText()
    t = window.t
    # Human summary: names/status/size result only.
    assert source.name in summary and artifact.path.name in summary
    assert "PNG→WEBP" in summary and t("succeeded") in summary
    assert t("journal_verified") in summary
    assert "event=" not in summary and str(source) not in summary
    assert "SHA-256" not in summary and "Кодек:" not in summary and "Codec:" not in summary
    # Existing Details tab is the single technical surface.
    request = c.request_snapshot
    assert request is not None
    expected_params = t(
        "journal_params",
        format=request.output_format,
        quality=request.quality,
        bounds=t("no_resize"),
        postfix=request.postfix,
        mode=t("journal_source_mode_keep"),
    )
    assert expected_params in details
    assert t("journal_sha", sha=artifact.sha256) in details
    assert artifact.path.name in details
    assert "event=conversion_started" in details and "event=conversion_finished" in details
    assert c.elapsed_seconds is not None
    # No second technical container/button/tab.
    assert not hasattr(window, "journal_toggle") and not hasattr(window, "log")
    assert window.tabs.count() == 2
    assert window.details.isReadOnly()
    assert window.details.focusPolicy() & Qt.FocusPolicy.StrongFocus
    flags = window.details.textInteractionFlags()
    assert flags & Qt.TextInteractionFlag.TextSelectableByMouse
    assert flags & Qt.TextInteractionFlag.TextSelectableByKeyboard
    assert window.details.lineWrapMode() == QPlainTextEdit.LineWrapMode.NoWrap
    window.details.setFocus()
    window.details.selectAll()
    assert window.details.textCursor().selectedText()


def test_details_raw_events_are_bounded_and_never_in_summary(window, app):
    for index in range(600):
        window._append_raw_event(f"event=synthetic_tick index={index}")
    assert len(window._raw_events) == 500
    assert window._raw_events[-1] == "event=synthetic_tick index=599"
    details = window.details.toPlainText()
    assert "event=synthetic_tick index=599" in details
    assert "event=synthetic_tick index=0" not in details
    assert "event=" not in window.journal_summary.toPlainText()


def test_checked_deletion_reported_in_summary_and_details(
    window, app, image_factory, monkeypatch,
):
    source = image_factory()
    c = add(app, window, [source])

    def forbidden(*args, **kwargs):
        raise AssertionError("A destructive consent modal must not be shown")

    monkeypatch.setattr(QMessageBox, "exec", forbidden)
    click_checkbox(window.settings.delete_original)
    window.start_button.click()
    pump(app, lambda: not c.busy)
    assert c.result.counts.deleted == 1 and not source.exists()
    summary = window.journal_summary.toPlainText()
    assert window.t("deletion_summary", deleted=1, retained=0, unknown=0) in summary
    assert window.t("source_deleted") in summary
    details = window.details.toPlainText()
    assert window.t("source_deleted") in details
    assert window.t("journal_source_mode_delete") in details
    assert "deleted=1" in details and "event=" in details
    assert "event=" not in summary


def test_failed_batch_never_invents_savings(window, app, tmp_path):
    bad = tmp_path / "corrupt.png"
    bad.write_bytes(b"synthetic corrupt PNG")
    c = add(app, window, [bad])
    window.start_button.click()
    pump(app, lambda: not c.busy)
    assert c.result.status == "failed"
    summary = window.journal_summary.toPlainText()
    assert window.t("failed") in summary
    assert window.t("journal_verified") not in summary
    assert "event=" not in summary
    assert "reason=INVALID_IMAGE" in window.details.toPlainText()


def test_running_and_partial_states_are_truthful(window, app, image_factory, tmp_path, monkeypatch):
    good = image_factory()
    bad = tmp_path / "partial-bad.png"
    bad.write_bytes(b"synthetic corrupt PNG")
    c = add(app, window, [good, bad])
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
        running = window.journal_summary.toPlainText()
        assert window.t("converting") in running
        assert window.t("journal_verified") not in running and "event=" not in running
        assert window.stop_button.isEnabled()
    finally:
        release.set()
        pump(app, lambda: not c.busy)
    assert c.result.status == "partial"
    summary = window.journal_summary.toPlainText()
    assert window.t("partial") in summary
    assert window.t("journal_verified") in summary
    assert window.t("journal_no_size") in summary


def test_size_line_typed_outcomes(window):
    t = window.t

    def item(source_size, output_size, publication="verified"):
        return ItemResult(
            index=0,
            source=Path("synthetic.png"),
            destination=Path("synthetic.webp"),
            status="succeeded",
            source_format="PNG",
            source_size_bytes=source_size,
            artifact=Artifact(
                path=Path("synthetic.webp"),
                format="WEBP",
                width=400,
                height=300,
                size_bytes=output_size,
                sha256="0" * 64,
                publication=publication,
            ),
        )

    assert window._size_line(item(1000, 400)) == (
        t("journal_saved", size=t.size(600), percent=60) + " · " + t("journal_verified")
    )
    assert window._size_line(item(1000, 1600)) == (
        t("journal_larger", size=t.size(600), percent=60) + " · " + t("journal_verified")
    )
    assert window._size_line(item(1000, 1000)) == (
        t("journal_same") + " · " + t("journal_verified")
    )
    assert window._size_line(item(1000, 400, "unverified")) == t("journal_unverified")
    assert window._size_line(item(None, 400)) == t("journal_no_size")


@pytest.mark.parametrize("size", ((1120, 760), (900, 640)))
def test_locale_theme_and_minimum_keep_result_and_tabs(window, app, image_factory, size):
    source = image_factory()
    c = add(app, window, [source])
    convert(app, window)
    raw_events = tuple(window._raw_events)
    window.resize(*size)
    window.theme_combo.setCurrentIndex(1)
    window.locale_combo.setCurrentIndex(1)
    app.processEvents()
    window.layout().activate()
    app.processEvents()
    assert c.result is not None and c.result.status == "succeeded"
    assert window.tabs.count() == 2 and window.tabs.currentIndex() == 0
    assert tuple(window._raw_events) == raw_events
    summary = window.journal_summary.toPlainText()
    assert window.language == "en" and source.name in summary
    assert "Succeeded" in summary and "event=" not in summary
    window.tabs.setCurrentIndex(1)
    app.processEvents()
    assert "event=conversion_finished" in window.details.toPlainText()
    window.tabs.setCurrentIndex(0)
    app.processEvents()
    assert window.tabs.currentIndex() == 0
    assert window.tabs.height() == 132
    assert window.status_label.isVisible() and window.start_button.isVisible()
