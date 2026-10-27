"""Separate PyQt process: real threads/API plus minimum deletion-window interactions."""

import time
from threading import Event
from types import SimpleNamespace

import pytest
from PyQt6.QtCore import QObject, Qt
from PyQt6.QtWidgets import QApplication

from gui import main_window
from gui.worker import CompressionWorker
from image_compressor import imaging

from .conftest import assert_image


@pytest.fixture(scope="module")
def app():
    application = QApplication.instance() or QApplication([])
    application.setQuitOnLastWindowClosed(False)
    yield application


def pump(app, predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while not predicate():
        assert time.monotonic() < deadline, "Qt event deadline exceeded"
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()


def collect_worker(app, worker, cancel_first=False):
    results, legacy, logs, progress, files = [], [], [], [], []
    worker.result_ready.connect(results.append)
    worker.finished_processing.connect(
        lambda successful, errors: legacy.append((successful, errors))
    )
    worker.log_message.connect(logs.append)
    worker.progress_updated.connect(progress.append)
    worker.file_processed.connect(files.append)
    if cancel_first:
        worker.file_processed.connect(
            lambda name: worker.cancel(), Qt.ConnectionType.DirectConnection
        )
    try:
        worker.start()
        pump(app, lambda: not worker.isRunning() and bool(legacy))
        assert len(results) == len(legacy) == 1
        assert worker.result is results[0]
        return results[0], legacy[0], logs, progress, files
    finally:
        worker.cancel()
        assert worker.wait(30000)


def test_real_worker_native_deletion_and_default_false_control(app, image_factory):
    source = image_factory("PRIVATE_FILENAME_SENTINEL.png")
    before = source.read_bytes()
    # Old blanket True refusal is superseded: shared Windows owner must really delete.
    deleting = image_factory("PRIVATE_DELETE_SENTINEL.png")
    deleted, legacy, logs, _, _ = collect_worker(
        app, CompressionWorker([str(deleting)], 80, "WEBP", delete_original=True)
    )
    assert deleted.status == "succeeded" and legacy == (1, 0)
    assert deleted.counts.deleted == 1 and not deleting.exists()
    assert deleted.items[0].source_disposition == "deleted"
    assert any("deleted=1" in message for message in logs)
    assert all("PRIVATE_" not in message for message in logs)
    with assert_image(deleted.items[0].destination):
        pass
    assert not source.with_suffix(".webp").exists()
    result, legacy, logs, progress, files = collect_worker(
        app,
        CompressionWorker(
            [str(source), str(source)], 80, "WEBP", postfix="PRIVATE_POSTFIX_SENTINEL"
        ),
    )
    assert result.status == "succeeded" and legacy == (1, 0) and result.counts.duplicates == 1
    assert progress[-1] == 100 and files == [source.name]
    assert all("PRIVATE_" not in message for message in logs)
    assert any("published=1" in message for message in logs)
    with assert_image(result.items[0].destination):
        pass
    assert source.read_bytes() == before


def test_real_worker_cancel_and_partial(app, image_factory, tmp_path):
    sources = [image_factory(f"{index}.png") for index in range(3)]
    result, legacy, logs, progress, files = collect_worker(
        app, CompressionWorker([str(p) for p in sources], 80, "WEBP"), cancel_first=True
    )
    assert result.status == "cancelled" and legacy == (1, 0)
    assert result.counts.cancelled == 2 and result.counts.published == 1
    assert max(progress) < 100 and len(files) == 1
    bad = tmp_path / "PRIVATE_CORRUPT_SENTINEL.png"
    bad.write_bytes(b"CORRUPT")
    partial, legacy, logs, _, _ = collect_worker(
        app, CompressionWorker([str(sources[1]), str(bad)], 80, "WEBP")
    )
    assert partial.status == "partial" and legacy == (1, 1)
    assert all("PRIVATE_" not in message for message in logs)
    assert any("reason=INVALID_IMAGE" in message for message in logs)


class View:
    def __init__(self):
        self.enabled = False
        self.values = []

    def setEnabled(self, enabled):  # noqa: N802
        self.enabled = enabled

    def setValue(self, value):  # noqa: N802
        self.values.append(value)

    def append(self, message):
        self.values.append(message)

    def clear(self):
        self.values.clear()

    def showMessage(self, message):  # noqa: N802
        self.values.append(message)

    def update_label(self, message):
        self.values.append(message)


class Controller(QObject):
    """Unmodified production handlers bound to lightweight, nonvisual views."""

    handle_dropped_files = main_window.ImageCompressorGUI.handle_dropped_files
    start_compression = main_window.ImageCompressorGUI.start_compression
    stop_compression = main_window.ImageCompressorGUI.stop_compression
    compression_finished = main_window.ImageCompressorGUI.compression_finished
    _restore_controls = main_window.ImageCompressorGUI._restore_controls
    _thread_finished = main_window.ImageCompressorGUI._thread_finished
    closeEvent = main_window.ImageCompressorGUI.closeEvent  # noqa: N815
    clear_queue = main_window.ImageCompressorGUI.clear_queue

    def __init__(self, sources, delete=False):
        super().__init__()
        self.worker = self.last_result = self._pending_result = None
        self._close_pending = self.closed = False
        self._queue_generation = 0
        self.files_to_process = list(map(str, sources))
        for name in (
            "start_button",
            "stop_button",
            "clear_button",
            "progress_bar",
            "log_text",
            "drop_zone",
            "status",
        ):
            setattr(self, name, View())
        self.quality_widget = SimpleNamespace(get_value=lambda: 80)
        self.format_widget = SimpleNamespace(get_selected_format=lambda: "WEBP")
        self.file_options_widget = SimpleNamespace(
            get_delete_original=lambda: delete, get_postfix=lambda: "PRIVATE_POSTFIX_SENTINEL",
            delete_original_checkbox=View(),
        )
        self.resize_widget = SimpleNamespace(
            get_max_width=lambda: None, get_max_height=lambda: None, is_resize_enabled=lambda: False
        )
        self._restore_controls()

    def statusBar(self):  # noqa: N802
        return self.status

    def close(self):
        self.closed = True


def test_controller_result_does_not_release_before_thread_finished(app, image_factory, monkeypatch):
    source = image_factory()
    released = Event()
    workers, dialogs = [], []

    class DelayedWorker(CompressionWorker):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            workers.append(self)

        def run(self):
            super().run()
            released.wait(10)

    monkeypatch.setattr(main_window, "CompressionWorker", DelayedWorker)
    monkeypatch.setattr(
        main_window.QMessageBox, "information", lambda *args: dialogs.append(args[2])
    )
    controller = Controller([source])
    try:
        controller.start_compression()
        pump(app, lambda: controller._pending_result is not None)
        assert controller.worker.isRunning() and not controller.start_button.enabled
        controller.start_compression()
        assert len(workers) == 1 and not dialogs
        controller.stop_compression()
        assert controller.last_result is None and controller.worker is workers[0]
        assert not controller.start_button.enabled
        released.set()
        pump(app, lambda: controller.worker is None)
        assert controller.last_result.status == "succeeded" and len(dialogs) == 1
        assert controller.start_button.enabled and not controller.stop_button.enabled
        assert all("PRIVATE_" not in str(value) for value in controller.log_text.values)
    finally:
        released.set()
        for worker in workers:
            try:
                worker.cancel()
                worker.wait(30000)
            except RuntimeError:  # Production deleteLater already destroyed a completed QThread.
                pass


def test_controller_stop_close_wait_for_real_cancel_and_next_operation(
    app,
    image_factory,
    monkeypatch,
):
    source = image_factory()
    entered, released = Event(), Event()
    original = imaging.encode

    def paused(*args, **kwargs):
        prepared = original(*args, **kwargs)
        entered.set()
        released.wait(10)
        return prepared

    monkeypatch.setattr(imaging, "encode", paused)
    dialogs = []
    monkeypatch.setattr(
        main_window.QMessageBox, "information", lambda *args: dialogs.append(args[2])
    )
    controller = Controller([source])
    worker = None
    try:
        controller.start_compression()
        worker = controller.worker
        assert entered.wait(10)
        # If production stop accidentally blocks on wait(), this release happens
        # only after a test-side timer, and the elapsed assertion detects it.
        from threading import Timer

        safety_release = Timer(1, released.set)
        safety_release.start()
        started = time.monotonic()
        controller.stop_compression()
        elapsed = time.monotonic() - started
        safety_release.cancel()
        assert elapsed < 0.5
        assert controller.worker is worker and not controller.start_button.enabled
        ignored = []
        controller.closeEvent(
            SimpleNamespace(ignore=lambda: ignored.append(True), accept=lambda: None)
        )
        assert ignored == [True] and not controller.closed
        released.set()
        pump(app, lambda: controller.worker is None)
        assert controller.closed and controller.last_result.status == "cancelled"
        assert controller.last_result.counts.published == 0 and not dialogs
        # A separate fresh controller/worker/token uses the same real owner successfully.
        next_controller = Controller([source])
        next_controller.start_compression()
        pump(app, lambda: next_controller.worker is None)
        assert next_controller.last_result.status == "succeeded" and len(dialogs) == 1
    finally:
        released.set()
        if worker is not None:
            try:
                worker.cancel()
                worker.wait(30000)
            except RuntimeError:
                pass


def test_controller_global_refusal_and_validation_restore(app, image_factory, monkeypatch):
    source = image_factory()
    dialogs = []
    monkeypatch.setattr(
        main_window.QMessageBox, "information", lambda *args: dialogs.append(args[2])
    )
    monkeypatch.setattr(main_window.QMessageBox, "warning", lambda *args: None)
    from image_compressor import _windows_deletion as native

    monkeypatch.setattr(native, "available", lambda: False)  # Genuine unsupported boundary control.
    monkeypatch.setattr(main_window.QMessageBox, "question",
                        lambda *args: main_window.QMessageBox.StandardButton.Yes)
    controller = Controller([source], delete=True)
    controller.start_compression()
    pump(app, lambda: controller.worker is None)
    assert controller.last_result.status == "rejected" and len(dialogs) == 1
    assert "fixed NTFS" in dialogs[0]
    assert controller.start_button.enabled and not controller.stop_button.enabled
    controller.resize_widget.is_resize_enabled = lambda: True
    controller.start_compression()
    assert controller.worker is None and controller.start_button.enabled
    assert not controller.stop_button.enabled
    controller.handle_dropped_files([str(source)])
    assert controller.files_to_process == [str(source)]


@pytest.mark.parametrize("answer", ["no", "yes", "stale_queue", "stale_options"])
def test_real_legacy_window_destructive_consent(app, image_factory, monkeypatch, answer):
    source = image_factory("PRIVATE_LEGACY_PATH/PRIVATE_LEGACY_NAME.png")
    before = source.read_bytes()
    widget = main_window.ImageCompressorGUI()
    widget.show()
    widget.handle_dropped_files([str(source)])
    box = widget.file_options_widget.delete_original_checkbox
    assert box.isEnabled() and not box.isChecked()
    box.setChecked(True)
    calls, messages = [], []

    def question(*args):
        calls.append(args)
        assert args[-1] == main_window.QMessageBox.StandardButton.No
        if answer == "stale_queue":
            widget.clear_queue()
        elif answer == "stale_options":
            widget.quality_widget.slider.setValue(41)
        return (main_window.QMessageBox.StandardButton.No if answer == "no" else
                main_window.QMessageBox.StandardButton.Yes)

    monkeypatch.setattr(main_window.QMessageBox, "question", question)
    monkeypatch.setattr(main_window.QMessageBox, "information",
                        lambda *args: messages.append(args[2]))
    try:
        widget.start_compression()
        if answer == "yes":
            assert widget.worker is not None and not box.isEnabled()
            pump(app, lambda: widget.worker is None)
            result = widget.last_result
            assert result.status == "succeeded" and result.counts.deleted == 1
            assert result.options.delete_original is True and not source.exists()
            with assert_image(result.items[0].destination):
                pass
            assert "удалено оригиналов: 1" in messages[0]
            assert "PRIVATE_" not in widget.log_text.toPlainText()
            assert box.isEnabled()
        else:
            assert widget.worker is None and widget.last_result is None
            assert source.read_bytes() == before and not source.with_suffix(".webp").exists()
        assert len(calls) == 1
    finally:
        widget.close()
        pump(app, lambda: widget.worker is None)
        widget.deleteLater()
        app.processEvents()


@pytest.mark.parametrize("outcome", ["retained", "unknown", "cancelled"])
def test_legacy_worker_truthful_deletion_summary(app, image_factory, monkeypatch, outcome):
    from image_compressor import _windows_deletion as native

    source = image_factory()
    before = source.read_bytes()
    worker = CompressionWorker([str(source)], 80, "WEBP", delete_original=True)
    if outcome == "retained":
        monkeypatch.setattr(native._api().dll, "FlushFileBuffers", lambda raw: 0)
    elif outcome == "unknown":
        monkeypatch.setattr(native, "_confirm_deleted", lambda *args: False)
    else:
        original = native.DeletionGuard.flush_final

        def cancel(guard):
            original(guard)
            worker.cancel()

        monkeypatch.setattr(native.DeletionGuard, "flush_final", cancel)
    result, legacy, logs, _, _ = collect_worker(app, worker)
    assert result.status == ("cancelled" if outcome == "cancelled" else "partial")
    assert legacy == (1, 0 if outcome == "cancelled" else 1)
    assert result.counts.deleted == 0 and result.counts.succeeded == result.counts.published == 1
    assert result.items[0].source_disposition == ("unknown" if outcome == "unknown" else "retained")
    assert any("source_disposition=" in message for message in logs)
    with assert_image(result.items[0].destination):
        pass
    if outcome == "unknown":
        assert not source.exists()
    else:
        assert source.read_bytes() == before


@pytest.mark.parametrize("unknown", [False, True])
def test_real_legacy_partial_result_message_is_truthful(app, image_factory, monkeypatch, unknown):
    from image_compressor import _windows_deletion as native

    source = image_factory()
    widget = main_window.ImageCompressorGUI()
    widget.handle_dropped_files([str(source)])
    widget.file_options_widget.delete_original_checkbox.setChecked(True)
    monkeypatch.setattr(main_window.QMessageBox, "question",
                        lambda *args: main_window.QMessageBox.StandardButton.Yes)
    messages = []
    monkeypatch.setattr(main_window.QMessageBox, "information",
                        lambda *args: messages.append(args[2]))
    if unknown:
        monkeypatch.setattr(native, "_confirm_deleted", lambda *args: False)
    else:
        monkeypatch.setattr(native._api().dll, "FlushFileBuffers", lambda raw: 0)
    try:
        widget.start_compression()
        pump(app, lambda: widget.worker is None)
        assert widget.last_result.status == "partial" and widget.last_result.counts.deleted == 0
        assert "удалено оригиналов: 0" in messages[0]
        text = widget.log_text.toPlainText()
        assert "Новый файл готов." in text
        assert ("Завершение удаления не подтверждено" if unknown else "Оригинал не удалён") in text
        assert "Исходники сохранены" not in text
    finally:
        widget.close()
        pump(app, lambda: widget.worker is None)
        widget.deleteLater()
        app.processEvents()
