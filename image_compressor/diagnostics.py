"""Closed technical projection. Never pass paths, DTOs or exception objects to logging."""

from __future__ import annotations

import logging
from copy import copy
from typing import Literal

from .models import ErrorCode, OutputFormat, Stage

LOGGER = logging.getLogger("image_compressor")
EventName = Literal[
    "conversion_started",
    "item_finished",
    "conversion_finished",
    "cleanup_failed",
    "cli_finished",
]


def project(
    event: EventName,
    *,
    operation_id: str | None = None,
    stage: Stage | None = None,
    reason: ErrorCode | None = None,
    outcome: str | None = None,
    index: int | None = None,
    output_format: OutputFormat | None = None,
    quality: int | None = None,
    total: int | None = None,
    succeeded: int | None = None,
    failed: int | None = None,
    cancelled: int | None = None,
    published: int | None = None,
    size_bytes: int | None = None,
    duration_ms: int | None = None,
) -> str:
    # Callers supply only internal codes/counts, never arbitrary user strings.
    fields: dict[str, str | int | None] = {
        "event": event,
        "operation_id": operation_id,
        "stage": stage,
        "reason": reason.value if reason else None,
        "outcome": outcome,
        "index": index,
        "format": output_format.value if output_format else None,
        "quality": quality,
        "total": total,
        "succeeded": succeeded,
        "failed": failed,
        "cancelled": cancelled,
        "published": published,
        "size_bytes": size_bytes,
        "duration_ms": duration_ms,
    }
    return " ".join(f"{key}={value}" for key, value in fields.items() if value is not None)


def emit(message: str) -> None:
    """Use host logging sinks, without its raw handleError/traceback fallback.

    A shallow handler view keeps the actual stream/formatter/lock and leaves host
    handlers/settings untouched. Standard StreamHandler catches formatter/write
    errors itself; its default handleError would otherwise leak an exception.
    """
    try:
        if not LOGGER.isEnabledFor(logging.INFO):
            return
        record = LOGGER.makeRecord(LOGGER.name, logging.INFO, "", 0, message, (), None)
        if not LOGGER.filter(record):
            return
        current: logging.Logger | None = LOGGER
        while current is not None:
            for handler in current.handlers:
                if record.levelno < handler.level:
                    continue
                try:
                    guarded = copy(handler)
                    guarded.handleError = lambda record: None  # type: ignore[method-assign]
                    guarded.handle(record)
                except Exception:
                    pass  # Diagnostics never change product results or trigger retry.
            current = current.parent if current.propagate else None
    except Exception:
        pass


class SafeStreamHandler(logging.StreamHandler):  # type: ignore[type-arg]
    def handleError(self, record: logging.LogRecord) -> None:  # noqa: N802
        pass
