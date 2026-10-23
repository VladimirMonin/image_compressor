import os
import time
from dataclasses import replace
from threading import Event, Timer

import pytest
from PySide6.QtCore import QTimer

import image_compressor as api
from gui_pyside6_v2.controller import Options
from gui_pyside6_v2.window import MainWindow
from gui_pyside6_v2.workers import ApiWorker
from image_compressor import discovery, imaging
from image_compressor import filesystem as fs

from .conftest import add, assert_readback, convert, pump


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP"])
@pytest.mark.parametrize("quality", [0, 80, 100])
def test_real_window_batch_readback(window, app, image_factory, fmt, quality):
    source = image_factory("real_ӘҒҚҢӨҰҮҺІ.png")
    before = source.read_bytes()
    c = add(app, window, [source])
    window.settings.output_format.setCurrentIndex(0 if fmt == "JPEG" else 1)
    window.settings.quality.setValue(quality)
    window.settings.resize_check.setChecked(True)
    window.settings.max_width.setValue(192)
    window.settings.max_height.setValue(108)
    result = convert(app, window)
    assert result.status == "succeeded" and result.counts.published == 1
    assert result.options.quality == quality and result.options.recursive is False
    assert c.request_snapshot.inputs == (source,)
    assert not c.request_snapshot.delete_original
    assert_readback(result.items[0], fmt, (144, 108))
    assert source.read_bytes() == before
    assert c.model.rows[0].status == "succeeded"
    assert window.progress.value() == window.progress.maximum() == 1
    assert window.status_label.property("tone") == "success"


@pytest.mark.parametrize("fmt,index", [("HEIF", 2), ("AVIF", 3)])
def test_available_optional_format_through_real_selector(
    window,
    app,
    image_factory,
    fmt,
    index,
):
    capability = window.controller.capabilities.for_format(fmt)
    if not capability.encoder_available:
        assert not window.settings.output_format.model().item(index).isEnabled()
        pytest.skip(f"Optional encoder unavailable: {fmt} / {capability.reason}")
    source = image_factory()
    original = source.read_bytes()
    add(app, window, [source])
    window.settings.output_format.setCurrentIndex(index)
    result = convert(app, window)
    assert result.status == "succeeded" and result.options.output_format.value == fmt
    assert_readback(result.items[0], expected_format=fmt, expected_size=(400, 300))
    assert source.read_bytes() == original


def test_no_upscale_and_resize_off_defaults(window, app, image_factory):
    source = image_factory(size=(24, 18))
    assert not window.settings.resize_check.isChecked()
    assert window.settings.quality.value() == 80
    assert window.settings.output_format.currentData() == "WEBP"
    add(app, window, [source])
    window.settings.resize_check.setChecked(True)
    result = convert(app, window)
    assert_readback(result.items[0], expected_size=(24, 18))
    assert result.options.max_width == 1920 and result.options.max_height == 1080


def test_real_discovery_recursive_dedup_and_selection_issues(window, app, image_factory, tmp_path):
    a = image_factory("folder/top.png")
    b = image_factory("folder/nested/child.png")
    (a.parent / "ignored.txt").write_text("synthetic", encoding="utf-8")
    unsupported = tmp_path / "explicit.txt"
    unsupported.write_text("synthetic", encoding="utf-8")
    window.settings.recursive.setChecked(False)
    c = add(app, window, [a.parent, a, unsupported])
    assert c.paths == (a,)
    assert c.selection.duplicates == 1 and c.selection.ignored == 1
    assert c.selection.issues[0].error.code == api.ErrorCode.UNSUPPORTED_INPUT_EXTENSION
    assert "UNSUPPORTED_INPUT_EXTENSION" in window.details.toPlainText()
    assert window.subset_note.isVisible()
    window.settings.recursive.setChecked(True)
    assert c.paths == (a,)  # Changing next-add recursion does not silently rescan.
    add(app, window, [a.parent])
    assert c.paths == (a, b) and c.selection.duplicates == 1
    alias = tmp_path / "alias.png"
    os.link(a, alias)
    add(app, window, [alias])
    assert c.paths == (a, b) and c.selection.duplicates == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    window.clear_button.click()
    add(app, window, [empty])
    assert c.paths == () and not window.start_button.isEnabled()


def test_same_format_empty_postfix_repeat_and_clear_retains_bytes(window, app, image_factory):
    source = image_factory("same.webp")
    before = source.read_bytes()
    c = add(app, window, [source])
    window.settings.postfix.setText("")
    conflict = convert(app, window)
    assert conflict.items[0].error.code == api.ErrorCode.INPUT_OUTPUT_CONFLICT
    assert c.request_snapshot.postfix == ""
    window.settings.postfix.setText("_custom")
    good = convert(app, window)
    target = source.with_name("same_custom.webp")
    assert good.items[0].destination == target
    assert_readback(good.items[0])
    prior_output = target.read_bytes()
    again = convert(app, window)
    assert again.items[0].error.code == api.ErrorCode.OUTPUT_EXISTS
    assert window.status_label.property("tone") == "error"
    window.clear_button.click()
    assert not c.paths and c.result is None
    assert source.read_bytes() == before and target.read_bytes() == prior_output


def test_batch_target_conflict_and_partial_corruption(window, app, image_factory, tmp_path):
    sources = [image_factory("a.png"), image_factory("a.jpg"), image_factory("ok.png")]
    before = {path: path.read_bytes() for path in sources}
    add(app, window, sources)
    result = convert(app, window)
    assert result.status == "partial" and result.counts.failed == 2
    assert [item.error.code if item.error else None for item in result.items] == [
        api.ErrorCode.TARGET_CONFLICT,
        api.ErrorCode.TARGET_CONFLICT,
        None,
    ]
    assert_readback(result.items[2])
    assert not sources[0].with_suffix(".webp").exists()
    assert window.status_label.property("tone") == "warning"
    assert "TARGET_CONFLICT" in window.details.toPlainText()
    assert all(path.read_bytes() == data for path, data in before.items())
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"synthetic invalid PNG")
    window.clear_button.click()
    other = image_factory("other.png")
    add(app, window, [other, bad])
    result = convert(app, window)
    assert result.status == "partial" and result.counts.succeeded == result.counts.failed == 1
    assert result.items[1].error.code == api.ErrorCode.INVALID_IMAGE
    assert "INVALID_IMAGE" in window.details.toPlainText()
    assert_readback(result.items[0])


def test_publication_unverified_not_success(window, app, image_factory, monkeypatch):
    source = image_factory()
    before = source.read_bytes()
    add(app, window, [source])
    original = imaging.verify_image
    calls = 0

    def broken(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise fs.fail(api.ErrorCode.VERIFICATION_FAILED, "readback")
        return original(*args)

    monkeypatch.setattr(imaging, "verify_image", broken)
    result = convert(app, window)
    assert result.status == "partial" and result.counts.published == 1
    assert result.counts.succeeded == 0 and result.items[0].artifact.publication == "unverified"
    assert window.controller.model.rows[0].status == "unverified"
    assert "PUBLISHED_UNVERIFIED" in window.details.toPlainText()
    assert window.status_label.property("tone") != "success"
    assert source.read_bytes() == before
    with imaging.Image.open(result.items[0].destination) as image:
        image.load()
        assert image.format == "WEBP"


def test_cleanup_and_observer_warning_not_lost(window, app, image_factory, monkeypatch):
    source = image_factory()
    add(app, window, [source])
    original = fs.Staging.cleanup

    def cleanup(staging):
        assert original(staging)
        return False  # Controlled warning seam; no residue is left by this fixture.

    def observer_failure(self, event):
        raise ValueError("PRIVATE_OBSERVER_EXCEPTION")

    monkeypatch.setattr(fs.Staging, "cleanup", cleanup)
    monkeypatch.setattr(ApiWorker, "_progress", observer_failure)
    result = convert(app, window)
    assert result.status == "partial" and result.counts.succeeded == 1
    assert result.items[0].warnings[0].code == api.ErrorCode.TEMP_CLEANUP_FAILED
    assert result.warnings[0].code == api.ErrorCode.OBSERVER_FAILED
    assert "TEMP_CLEANUP_FAILED" in window.details.toPlainText()
    assert "OBSERVER_FAILED" in window.details.toPlainText()
    assert "PRIVATE_OBSERVER_EXCEPTION" not in window.log.toPlainText()
    assert_readback(result.items[0])


def test_stop_responsive_real_encode_and_next_run(window, app, image_factory, monkeypatch):
    source = image_factory()
    before = source.read_bytes()
    c = add(app, window, [source])
    entered, released = Event(), Event()
    original = imaging.encode

    def paused(*args, **kwargs):
        prepared = original(*args, **kwargs)
        entered.set()
        assert released.wait(10)
        return prepared

    monkeypatch.setattr(imaging, "encode", paused)
    heartbeat = []
    timer = QTimer()
    timer.setInterval(5)
    timer.timeout.connect(lambda: heartbeat.append(1))
    timer.start()
    try:
        window.start_button.click()
        worker = c.worker
        pump(app, entered.is_set)
        snapshot = c.request_snapshot
        prior_log = window.log.toPlainText()
        window.theme_combo.setCurrentIndex(1)
        window.locale_combo.setCurrentIndex(2)
        assert c.worker is worker and c.request_snapshot is snapshot and c.paths == (source,)
        assert window.settings.quality.value() == 80
        assert window.log.toPlainText() == prior_log and c.busy
        start_ticks = len(heartbeat)
        safety = Timer(1, released.set)
        safety.start()
        started = time.monotonic()
        window.stop_button.click()
        elapsed = time.monotonic() - started
        safety.cancel()
        assert elapsed < 0.4
        pump(app, lambda: len(heartbeat) > start_ticks + 3)
        assert c.worker is worker and c.state == "stop_requested"
        assert not c.start(Options()) and not window.start_button.isEnabled()
        assert not window.settings.form.isEnabled() and not window.add_button.isEnabled()
        released.set()
        pump(app, lambda: not c.busy)
        assert c.result.status == "cancelled" and c.result.counts.published == 0
        assert not source.with_suffix(".webp").exists()
        assert source.read_bytes() == before
        old_token = worker.token
        window.start_button.click()
        assert c.worker.token is not old_token and not c.worker.token.is_cancelled()
        pump(app, lambda: not c.busy)
        assert c.result.status == "succeeded"
        assert_readback(c.result.items[0])
    finally:
        released.set()
        timer.stop()
        pump(app, lambda: not c.busy)


@pytest.mark.parametrize("late", [False, True])
def test_stop_after_real_link_retains_outputs(window, app, image_factory, monkeypatch, late):
    sources = [image_factory("first.png")]
    if not late:
        sources.append(image_factory("second.png"))
    snapshots = {source: source.read_bytes() for source in sources}
    c = add(app, window, sources)
    original = fs.publish_new
    entered, released = Event(), Event()
    calls = 0

    def paused(*args):
        nonlocal calls
        original(*args)
        calls += 1
        if calls == 1:
            entered.set()
            assert released.wait(10)

    monkeypatch.setattr(fs, "publish_new", paused)
    try:
        window.start_button.click()
        pump(app, entered.is_set)
        window.stop_button.click()
        assert c.state == "stop_requested"
        released.set()
        pump(app, lambda: not c.busy)
        result = c.result
        assert result.status == ("succeeded" if late else "cancelled")
        assert result.counts.published == result.counts.succeeded == 1
        assert_readback(result.items[0])
        if not late:
            assert result.counts.cancelled == 1
            assert not sources[1].with_suffix(".webp").exists()
            assert window.progress.value() < window.progress.maximum()
        assert all(path.read_bytes() == data for path, data in snapshots.items())
    finally:
        released.set()
        pump(app, lambda: not c.busy)


def test_cancel_incomplete_discovery_preserves_old_queue(window, app, image_factory, monkeypatch):
    old = image_factory("old.png")
    candidate = image_factory("folder/new.png")
    c = add(app, window, [old])
    original = discovery._directory_children
    entered, released = Event(), Event()

    from contextlib import contextmanager

    @contextmanager
    def paused(path):
        with original(path) as children:
            entered.set()
            assert released.wait(10)
            yield children

    monkeypatch.setattr(discovery, "_directory_children", paused)
    try:
        window.add_paths((candidate.parent,))
        pump(app, entered.is_set)
        window.stop_button.click()
        released.set()
        pump(app, lambda: not c.busy)
        assert c.paths == (old,) and c.failure == api.ErrorCode.CANCELLED
        assert "CANCELLED" in window.details.toPlainText()
        assert not list(candidate.parent.glob("*.webp"))
        assert c.can_start
    finally:
        released.set()
        pump(app, lambda: not c.busy)


def test_result_ready_still_holds_thread_and_stale_is_ignored(
    window, app, image_factory, monkeypatch
):
    source = image_factory()
    c = add(app, window, [source])
    released = Event()

    class DelayedWorker(ApiWorker):
        def run(self):
            super().run()
            assert released.wait(10)

    import gui_pyside6_v2.controller as controller_module

    monkeypatch.setattr(controller_module, "ApiWorker", DelayedWorker)
    try:
        window.start_button.click()
        pump(app, lambda: c.result is not None)
        assert c.busy and c.worker.isRunning() and not c.can_start
        good = c.result
        c._delivered(c.generation - 1, "conversion", api.BatchResult("failed"))
        assert c.result is good  # Positive live delivery above, not all signals disabled.
        c._progressed(c.generation - 1, api.ProgressEvent("finished", None, 99, 0, 0, 0, 0))
        assert c.progress is None or c.progress.total != 99
        assert not c.start(Options())
        released.set()
        pump(app, lambda: not c.busy)
        assert c.can_start and c.result.status == "succeeded"
    finally:
        released.set()
        pump(app, lambda: not c.busy)


@pytest.mark.parametrize("kind", ["capabilities", "discovery", "conversion"])
def test_close_is_deferred_until_real_thread_finished(app, image_factory, monkeypatch, kind):
    entered, released = Event(), Event()
    original_run = ApiWorker.run

    def delayed(self):
        if self.kind == kind:
            entered.set()
            assert released.wait(10)
        original_run(self)

    monkeypatch.setattr(ApiWorker, "run", delayed)
    widget = MainWindow()
    widget.show()
    c = widget.controller
    source = image_factory()
    try:
        if kind != "capabilities":
            pump(app, lambda: not c.busy and c.capabilities is not None)
            if kind == "conversion":
                add(app, widget, [source])
                widget.start_button.click()
            else:
                widget.add_paths((source,))
        pump(app, entered.is_set)
        started = time.monotonic()
        assert not widget.close()
        assert time.monotonic() - started < 0.4 and widget.isVisible() and c.closing
        assert c.busy
        released.set()
        pump(app, lambda: not widget.isVisible() and not c.busy)
        assert not source.with_suffix(".webp").exists()
    finally:
        released.set()
        pump(app, lambda: not c.busy)
        widget.close()
        widget.deleteLater()
        app.processEvents()


def test_close_before_scheduled_dispatch_starts_no_worker(app):
    widget = MainWindow()
    assert widget.close()
    app.processEvents()
    assert widget.controller.worker is None and widget.controller.closing
    widget.deleteLater()
    app.processEvents()


def test_technical_sink_nonempty_and_no_private_data(window, app, image_factory, monkeypatch):
    source = image_factory("PRIVATE_FILENAME_SENTINEL.webp")
    c = add(app, window, [source])
    window.settings.postfix.setText("_PRIVATE_POSTFIX_SENTINEL")
    result = convert(app, window)
    assert result.status == "succeeded"
    assert "PRIVATE_FILENAME_SENTINEL" in c.model.rows[0].path.name
    assert "PRIVATE_POSTFIX_SENTINEL" in window.details.toPlainText()
    log = window.log.toPlainText()
    assert "event=conversion_finished" in log and "published=1" in log
    assert "PRIVATE_" not in log
    window.clear_button.click()
    other = image_factory("PRIVATE_ERROR_SENTINEL.png")
    add(app, window, [other])

    def broken(*args):
        raise ValueError("PRIVATE_RAW_EXCEPTION_SENTINEL")

    monkeypatch.setattr(imaging, "encode", broken)
    result = convert(app, window)
    assert result.items[0].error.code == api.ErrorCode.INTERNAL_ERROR
    log = window.log.toPlainText()
    assert "reason=INTERNAL_ERROR" in log and "PRIVATE_" not in log
    assert "Traceback" not in log and str(source.parent) not in log


def test_unavailable_encoder_and_delete_visible(window, app, image_factory):
    c = add(app, window, [image_factory()])
    c.capabilities = replace(
        c.capabilities,
        formats=tuple(
            replace(item, encoder_available=False, reason="ENCODE_FAILED")
            if item.format == "HEIF"
            else item
            for item in c.capabilities.formats
        ),
    )
    c.changed.emit()
    model = window.settings.output_format.model()
    assert not model.item(2).isEnabled()
    assert "ENCODE_FAILED" in model.item(2).toolTip()
    window.settings.output_format.setCurrentIndex(2)  # A programmatic bypass still cannot Start.
    assert not window.start_button.isEnabled()
    assert c.worker is None
    control = window.settings.delete_original
    assert control.isVisible() and not control.isEnabled() and not control.isChecked()
    assert window.settings.safety_explanation.isVisible()
    rejected = api.convert(api.ConversionRequest(c.paths, delete_original=True))
    assert (
        rejected.status == "rejected"
        and rejected.errors[0].code == api.ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED
    )
    assert not c.paths[0].with_suffix(".webp").exists()


def test_coalesced_progress_keeps_latest_while_next_codec_waits(
    window,
    app,
    image_factory,
    monkeypatch,
):
    from PySide6.QtTest import QTest

    import gui_pyside6_v2.workers as workers

    sources = [image_factory("first.png"), image_factory("second.png")]
    c = add(app, window, sources)
    entered, released = Event(), Event()
    original = imaging.encode
    calls = 0

    def paused(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            entered.set()
            assert released.wait(10)
        return original(*args)

    monkeypatch.setattr(imaging, "encode", paused)
    monkeypatch.setattr(workers, "monotonic", lambda: 100.0)
    try:
        window.start_button.click()
        pump(app, entered.is_set)
        QTest.qWait(100)
        assert window.progress.maximum() == 2 and window.progress.value() == 1
        assert c.progress.total == 2 and c.progress.processed == 1
        assert c.model.rows[0].status == "succeeded"
        assert c.model.rows[1].status == "waiting"
    finally:
        released.set()
        pump(app, lambda: not c.busy)
