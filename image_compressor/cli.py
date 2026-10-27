"""Non-interactive adapter: syntax, signals, JSON delivery and exit codes only."""

from __future__ import annotations

import argparse
import json
import logging
import signal
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from types import FrameType
from typing import Any, NoReturn

from . import __version__, convert, diagnostics, get_capabilities
from .models import (
    BatchResult,
    CancellationToken,
    ConversionRequest,
    ErrorCode,
    ProgressEvent,
    error,
)
from .serialization import JSONValue, envelope


class _UsageError(Exception):
    pass


class _EarlyExitError(Exception):
    pass


class _Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        raise _UsageError  # Never echo message/argv (including argparse's type errors).

    def exit(self, status: int = 0, message: str | None = None) -> NoReturn:
        if status:
            raise _UsageError
        raise _EarlyExitError


def _parser() -> _Parser:
    parser = _Parser(prog="image-compressor", description="Create verified new image files.")
    parser.add_argument("--version", action="version", version=f"image-compressor {__version__}")
    commands = parser.add_subparsers(dest="command", required=True)
    capabilities = commands.add_parser(
        "capabilities", help="Probe local codecs using synthetic images"
    )
    capabilities.add_argument("--json", action="store_true", help="JSON output (always enabled)")
    conversion = commands.add_parser("convert", help="Convert files or directory snapshots")
    conversion.add_argument("inputs", nargs="+")
    conversion.add_argument("--recursive", action="store_true")
    conversion.add_argument("--format", dest="output_format", default="WEBP")
    conversion.add_argument("--quality", type=int, default=80)
    conversion.add_argument("--max-width", type=int)
    conversion.add_argument("--max-height", type=int)
    output = conversion.add_mutually_exclusive_group()
    output.add_argument("--output", dest="output_path")
    output.add_argument("--output-dir", dest="output_directory")
    conversion.add_argument("--postfix", default="_compressed")
    conversion.add_argument(
        "--delete-original", action="store_true", default=False,
        help=("Permanently delete originals after verified new output; not Recycle Bin, "
              "no automatic recovery. Guarded Windows local fixed NTFS only."),
    )
    conversion.add_argument("--json", action="store_true", help="JSON output (always enabled)")
    conversion.add_argument("--progress", action="store_true", help="Safe item counts to stderr")
    return parser


@contextmanager
def _sink() -> Iterator[None]:
    logger = diagnostics.LOGGER
    handler = diagnostics.SafeStreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    old_level, old_propagate = logger.level, logger.propagate
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        yield
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
        logger.propagate = old_propagate
        try:
            handler.flush()
            handler.close()
        except Exception:
            pass


@contextmanager
def _signals(token: CancellationToken) -> Iterator[None]:
    previous: list[tuple[signal.Signals, Any]] = []

    def cancel(signum: int, frame: FrameType | None) -> None:
        token.cancel()

    try:
        for sig in (signal.SIGINT, getattr(signal, "SIGBREAK", None)):
            if sig is None:
                continue
            try:
                old = signal.signal(sig, cancel)
                previous.append((sig, old))
            except (ValueError, OSError):
                diagnostics.emit(
                    diagnostics.project(
                        "cli_finished",
                        stage="cli",
                        reason=ErrorCode.SIGNAL_UNAVAILABLE,
                        outcome="limited",
                    )
                )
        yield
    finally:
        for sig, old in reversed(previous):
            signal.signal(sig, old)


def exit_code(result: BatchResult) -> int:
    infos = [*result.errors, *(item.error for item in result.items if item.error)]
    if any(info.code == ErrorCode.INTERNAL_ERROR for info in infos):
        return 5
    return {"succeeded": 0, "rejected": 2, "partial": 3, "failed": 4, "cancelled": 130}[
        result.status
    ]


def _deliver(payload: dict[str, JSONValue]) -> bool:
    try:
        # Explicit UTF-8 even on a Windows pipe using a legacy locale.
        reconfigure = getattr(sys.stdout, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="strict")
        sys.stdout.write(json.dumps(payload, ensure_ascii=False, allow_nan=False) + "\n")
        sys.stdout.flush()
        return True
    except (OSError, ValueError, UnicodeError):
        # Avoid a second interpreter-shutdown flush of a physically broken pipe.
        try:
            sys.stdout.close()
        except (OSError, ValueError):
            pass
        return False


def main(argv: Sequence[str] | None = None) -> int:
    command: str | None = None
    with _sink():
        try:
            args = _parser().parse_args(argv)
            command = args.command
            if command == "capabilities":
                diagnostics.emit(diagnostics.project("conversion_started", stage="capabilities"))
                capabilities = get_capabilities()
                payload = envelope(command, "succeeded", capabilities)
                code = 0
            else:
                token = CancellationToken()
                request = ConversionRequest(
                    args.inputs,
                    output_format=args.output_format,
                    quality=args.quality,
                    max_width=args.max_width,
                    max_height=args.max_height,
                    recursive=args.recursive,
                    output_directory=args.output_directory,
                    output_path=args.output_path,
                    postfix=args.postfix,
                    delete_original=args.delete_original,
                )
                with _signals(token):
                    # Normal diagnostics already include every terminal item; --progress
                    # additionally exposes safe processed counts, not paths or codec ticks.
                    def progress(event: ProgressEvent) -> None:
                        if event.phase == "item_finished":
                            diagnostics.emit(
                                diagnostics.project(
                                    "item_finished",
                                    stage="observer",
                                    index=event.index,
                                    total=event.total,
                                    succeeded=event.succeeded,
                                    failed=event.failed,
                                    cancelled=event.cancelled,
                                )
                            )

                    result = convert(
                        request, cancellation=token, on_progress=progress if args.progress else None
                    )
                payload = envelope(command, result.status, result, result.errors)
                code = exit_code(result)
        except _EarlyExitError:
            return 0
        except _UsageError:
            info = error(ErrorCode.CLI_USAGE, "cli")
            payload = envelope(command, "rejected", None, (info,))
            code = 2
        except Exception:
            info = error(ErrorCode.INTERNAL_ERROR, "cli")
            payload = envelope(command, "failed", None, (info,))
            code = 5
        diagnostics.emit(
            diagnostics.project(
                "cli_finished",
                stage="cli",
                outcome="succeeded" if code == 0 else "not_succeeded",
                reason=ErrorCode.CLI_USAGE if code == 2 and command is None else None,
            )
        )
        if not _deliver(payload):
            diagnostics.emit(
                diagnostics.project("cli_finished", stage="cli", reason=ErrorCode.DELIVERY_FAILED)
            )
            return 5
        return code
