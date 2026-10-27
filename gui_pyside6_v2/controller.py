"""GUI-thread state owner; one QThread and a fresh API token per operation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from PySide6.QtCore import QObject, QTimer, Signal, Slot

import image_compressor as api

from .queue_model import QueueModel
from .workers import AdapterFailure, ApiWorker, Selection

State = Literal[
    "initializing",
    "empty",
    "ready",
    "discovering",
    "converting",
    "stop_requested",
    "terminal",
    "closing",
]


@dataclass(frozen=True)
class Options:
    output_format: str = "WEBP"
    quality: int = 80
    resize: bool = False
    max_width: int = 1920
    max_height: int = 1080
    postfix: str = "_compressed"
    delete_original: bool = False


class Controller(QObject):
    changed = Signal()
    log_line = Signal(str)
    close_ready = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.model = QueueModel(self)
        self.state: State = "initializing"
        self.capabilities: api.Capabilities | None = None
        self.selection: api.DiscoveryResult | None = None
        self.result: api.BatchResult | None = None
        self.failure: api.ErrorCode | None = None
        self.progress: api.ProgressEvent | None = None
        self.worker: ApiWorker | None = None
        self.generation = 0
        self.closing = False
        self._after: State = "empty"
        self._received = False
        self.request_snapshot: api.ConversionRequest | None = None
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(40)
        self._progress_timer.timeout.connect(self._poll_progress)

    @property
    def busy(self) -> bool:
        return self.worker is not None

    @property
    def paths(self) -> tuple[Path, ...]:
        return tuple(row.path for row in self.model.rows)

    @property
    def can_start(self) -> bool:
        return bool(
            self.paths and self.capabilities is not None and not self.busy and not self.closing
        )

    def _launch(self, worker: ApiWorker, state: State) -> None:
        assert self.worker is None
        self.worker = worker
        self._received = False
        self.state = state
        worker.delivered.connect(self._delivered)
        worker.progressed.connect(self._progressed)
        worker.finished.connect(self._finished)
        self.changed.emit()
        if worker.kind == "conversion":
            self._progress_timer.start()
        worker.start()

    @Slot()
    def initialize(self) -> None:
        # Also protects a close that happens before the singleShot dispatch.
        if self.closing or self.busy or self.capabilities is not None:
            return
        self.generation += 1
        self.failure = None
        self._launch(ApiWorker(self.generation, "capabilities", parent=self), "initializing")

    def add_paths(self, paths: tuple[Path, ...], *, recursive: bool) -> bool:
        if not paths or self.busy or self.closing or self.capabilities is None:
            return False
        self.generation += 1
        self.failure = None
        self.progress = None
        self._launch(
            ApiWorker(
                self.generation,
                "discovery",
                paths=(*self.paths, *paths),
                recursive=recursive,
                parent=self,
            ),
            "discovering",
        )
        self.log_line.emit("event=selection_started")
        return True

    def start(self, options: Options) -> bool:
        if not self.can_start:
            return False
        self.generation += 1
        self.failure = None
        self.progress = None
        self.result = None
        self.model.reset_statuses()
        self.request_snapshot = api.ConversionRequest(
            self.paths,
            output_format=options.output_format,
            quality=options.quality,
            max_width=options.max_width if options.resize else None,
            max_height=options.max_height if options.resize else None,
            postfix=options.postfix,
            recursive=False,
            delete_original=options.delete_original,
        )
        self.log_line.emit(f"event=conversion_started total={len(self.paths)}")
        self._launch(
            ApiWorker(self.generation, "conversion", request=self.request_snapshot, parent=self),
            "converting",
        )
        return True

    @Slot()
    def stop(self) -> None:
        if self.worker is None or self.worker.kind == "capabilities":
            return
        self.worker.token.cancel()  # Direct, thread-safe; never queued behind the codec.
        self.state = "closing" if self.closing else "stop_requested"
        self.log_line.emit("event=stop_requested")
        self.changed.emit()

    @Slot()
    def clear(self) -> None:
        if self.busy or self.closing:
            return
        self.generation += 1
        self.model.replace_selection((), ())
        self.selection = None
        self.result = None
        self.progress = None
        self.failure = None
        self.request_snapshot = None
        self.state = "empty"
        self.log_line.emit("event=queue_cleared total=0")
        self.changed.emit()

    def request_close(self) -> bool:
        self.closing = True
        if self.worker is None:
            return True
        self.state = "closing"
        self.stop()
        self.changed.emit()
        return False

    @Slot()
    def _poll_progress(self) -> None:
        worker = self.worker
        if worker is not None and worker.kind == "conversion":
            self.model.apply_items(worker.take_completed_items())
            event = worker.latest_progress()
            if event is not None and event is not self.progress:
                self._progressed(worker.generation, event)

    @Slot(int, object)
    def _progressed(self, generation: int, event: object) -> None:
        if (
            generation != self.generation
            or self.worker is None
            or not isinstance(event, api.ProgressEvent)
        ):
            return
        self.progress = event
        if event.item is not None:
            self.model.apply_item(event.item)
        # index is only an API batch index, not an assumed preview row identity.
        self.changed.emit()

    @Slot(int, str, object)
    def _delivered(self, generation: int, kind: str, payload: object) -> None:
        if generation != self.generation or self.worker is None:
            return
        if kind != self.worker.kind:
            return
        self._received = True
        if isinstance(payload, AdapterFailure):
            self.failure = payload.code
            self._after = "terminal"
            self.log_line.emit(f"event=adapter_failed reason={payload.code.value}")
        elif kind == "capabilities" and isinstance(payload, api.Capabilities):
            self.capabilities = payload
            self._after = "ready" if self.paths else "empty"
            self.log_line.emit("event=capabilities_finished")
        elif kind == "discovery" and isinstance(payload, Selection):
            result = payload.result
            # Incomplete/cancelled preview never replaces the prior runnable queue.
            if (
                result.discovery_complete
                and not self.worker.token.is_cancelled()
                and not result.errors
            ):
                self.model.replace_selection(result.paths, payload.sizes)
                self.selection = result
                self.result = None
                self._after = "ready" if result.paths else "empty"
            else:
                self._after = "terminal"
                self.failure = result.errors[0].code if result.errors else api.ErrorCode.CANCELLED
                # Preserve both the previous selection and a visible cancellation/failure.
            self.log_line.emit(
                f"event=selection_finished available={len(result.paths)} "
                f"issues={len(result.issues)} "
                f"duplicates={result.duplicates} ignored={result.ignored} "
                f"complete={int(result.discovery_complete)}"
            )
            for info in (*result.errors, *result.warnings):
                self.log_line.emit(f"event=selection_notice reason={info.code.value}")
        elif kind == "conversion" and isinstance(payload, api.BatchResult):
            self.result = payload
            self._after = "terminal"
            self.model.apply_items(payload.items)
            c = payload.counts
            self.log_line.emit(
                f"event=conversion_finished outcome={payload.status} total={c.total} "
                f"succeeded={c.succeeded} failed={c.failed} cancelled={c.cancelled} "
                f"published={c.published} deleted={c.deleted} "
                f"duplicates={c.duplicates} ignored={c.ignored}"
            )
            for info in (*payload.errors, *payload.warnings):
                self.log_line.emit(
                    f"event=batch_notice reason={info.code.value} stage={info.stage}"
                )
            for item in payload.items:
                self.log_line.emit(
                    f"event=item_finished index={item.index} "
                    f"source_disposition={item.source_disposition}"
                )
                for info in (*item.warnings, *((item.error,) if item.error else ())):
                    self.log_line.emit(
                        f"event=item_notice index={item.index} reason={info.code.value}"
                    )
        else:
            self.failure = api.ErrorCode.INTERNAL_ERROR
            self._after = "terminal"
        # Result-ready is NOT QThread.finished. Gating/lifetime remain in force here.
        self.changed.emit()

    @Slot()
    def _finished(self) -> None:
        worker = self.sender()
        if worker is not self.worker:
            return
        assert isinstance(worker, ApiWorker)
        self.worker = None
        self._progress_timer.stop()
        if not self._received:
            self.failure = api.ErrorCode.INTERNAL_ERROR
            self._after = "terminal"
            self.log_line.emit("event=adapter_failed reason=INTERNAL_ERROR")
        worker.deleteLater()
        self.state = "closing" if self.closing else self._after
        self.changed.emit()
        if self.closing:
            self.close_ready.emit()
