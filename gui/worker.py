"""QThread transport for the single synchronous application owner."""

from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from image_compressor import (
    BatchResult,
    CancellationToken,
    ConversionRequest,
    ErrorCode,
    ProgressEvent,
    convert,
)
from image_compressor.diagnostics import project

DESTRUCTIVE_MODE_MESSAGE = (
    "Удаление требует защищённого доступа к локальному fixed NTFS на Windows. "
    "Без этого доступно преобразование с сохранением оригиналов."
)


class CompressionWorker(QThread):
    progress_updated = pyqtSignal(int)
    file_processed = pyqtSignal(str)
    log_message = pyqtSignal(str)
    finished_processing = pyqtSignal(int, int)
    result_ready = pyqtSignal(object)

    def __init__(
        self,
        files: list[str],
        quality: int,
        format_type: str,
        delete_original: bool = False,
        postfix: str = "_compressed",
        max_width: int | None = None,
        max_height: int | None = None,
    ):
        super().__init__()
        self.files = tuple(files)
        self.quality = quality
        self.format_type = format_type
        self.delete_original = delete_original
        self.postfix = postfix
        self.max_width = max_width
        self.max_height = max_height
        self._cancellation = CancellationToken()
        self.result: BatchResult | None = None

    @property
    def is_cancelled(self) -> bool:
        return self._cancellation.is_cancelled()

    def _progress(self, event: ProgressEvent) -> None:
        if event.total and event.phase == "item_finished":
            self.progress_updated.emit(int(event.processed / event.total * 100))
        if event.item is not None:
            self.log_message.emit(
                project(
                    "item_finished",
                    index=event.item.index,
                    outcome=event.item.status,
                    stage=event.item.error.stage if event.item.error else
                          (event.item.warnings[0].stage if event.item.warnings else "readback"),
                    reason=event.item.error.code if event.item.error else
                           (event.item.warnings[0].code if event.item.warnings else None),
                    source_disposition=event.item.source_disposition,
                    deleted=int(event.item.source_disposition == "deleted"),
                )
            )
            if event.item.status == "succeeded":
                self.file_processed.emit(Path(event.item.source).name)

    def run(self) -> None:
        self.log_message.emit(project("conversion_started"))
        self.result = convert(
            ConversionRequest(
                self.files,
                quality=self.quality,
                output_format=self.format_type,
                recursive=True,
                delete_original=self.delete_original,
                postfix=self.postfix,
                max_width=self.max_width,
                max_height=self.max_height,
            ),
            cancellation=self._cancellation,
            on_progress=self._progress,
        )
        counts = self.result.counts
        for info in self.result.errors:
            self.log_message.emit(
                project(
                    "conversion_finished",
                    outcome=self.result.status,
                    reason=info.code,
                    stage=info.stage,
                )
            )
            if info.code == ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED:
                self.log_message.emit(DESTRUCTIVE_MODE_MESSAGE)
        self.log_message.emit(
            project(
                "conversion_finished",
                outcome=self.result.status,
                total=counts.total,
                succeeded=counts.succeeded,
                failed=counts.failed,
                cancelled=counts.cancelled,
                published=counts.published,
                deleted=counts.deleted,
            )
        )
        self.result_ready.emit(self.result)
        deletion_issues = sum(
            item.status == "succeeded" and any(
                info.stage == "source_deletion"
                and info.code not in (ErrorCode.CANCELLED, ErrorCode.INTERNAL_ERROR)
                for info in item.warnings
            )
            for item in self.result.items
        )
        errors = counts.failed + len(self.result.errors) + deletion_issues
        if self.result.status == "rejected":
            errors = max(1, errors)
        self.finished_processing.emit(counts.succeeded, errors)

    def cancel(self) -> None:
        self._cancellation.cancel()
