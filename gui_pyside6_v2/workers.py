"""Thread transport only. All discovery/codec/file policy remains in the public API."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from time import monotonic
from typing import Literal

from PySide6.QtCore import QObject, QThread, Signal

import image_compressor as api

Kind = Literal["capabilities", "discovery", "conversion"]


@dataclass(frozen=True)
class Selection:
    result: api.DiscoveryResult
    sizes: tuple[int | None, ...]


@dataclass(frozen=True)
class AdapterFailure:
    """No raw exception/path crosses the technical error channel."""

    code: api.ErrorCode = api.ErrorCode.INTERNAL_ERROR


class ApiWorker(QThread):
    delivered = Signal(int, str, object)
    progressed = Signal(int, object)

    def __init__(
        self,
        generation: int,
        kind: Kind,
        *,
        paths: tuple[Path, ...] = (),
        recursive: bool = False,
        request: api.ConversionRequest | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.generation = generation
        self.kind = kind
        self.paths = paths
        self.recursive = recursive
        self.request = request
        self.token = api.CancellationToken()
        self._last_tick = 0.0
        self._progress_lock = Lock()
        self._latest_progress: api.ProgressEvent | None = None
        self._completed_items: list[api.ItemResult] = []

    def take_completed_items(self) -> tuple[api.ItemResult, ...]:
        with self._progress_lock:
            items = tuple(self._completed_items)
            self._completed_items.clear()
            return items

    def latest_progress(self) -> api.ProgressEvent | None:
        with self._progress_lock:
            return self._latest_progress

    def _progress(self, event: api.ProgressEvent) -> None:
        with self._progress_lock:
            self._latest_progress = event
            if event.item is not None:
                self._completed_items.append(event.item)
        now = monotonic()
        # At most ~25 queued ticks/sec. The final immutable result restores every row/count.
        if event.phase == "finished" or now - self._last_tick >= 0.04:
            self._last_tick = now
            self.progressed.emit(self.generation, event)

    def run(self) -> None:
        payload: object
        try:
            if self.kind == "capabilities":
                payload = api.get_capabilities()
            elif self.kind == "discovery":
                result = api.discover_inputs(
                    self.paths, recursive=self.recursive, cancellation=self.token
                )
                sizes: list[int | None] = []
                for path in result.paths:
                    if self.token.is_cancelled():
                        sizes.append(None)
                        continue
                    try:
                        sizes.append(path.stat().st_size)
                    except OSError:
                        sizes.append(None)
                payload = Selection(result, tuple(sizes))
            else:
                assert self.request is not None
                payload = api.convert(
                    self.request, cancellation=self.token, on_progress=self._progress
                )
        except Exception:
            payload = AdapterFailure()
        self.delivered.emit(self.generation, self.kind, payload)
