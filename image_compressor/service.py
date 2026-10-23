"""The synchronous application owner. Adapters never perform conversion/file effects."""

from __future__ import annotations

import stat
from collections import Counter
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from time import monotonic
from typing import Literal
from uuid import uuid4

from . import diagnostics, discovery, imaging
from . import filesystem as fs
from .models import (
    Artifact,
    BatchResult,
    BatchStatus,
    CancellationToken,
    ConversionRequest,
    Counts,
    EffectiveOptions,
    ErrorCode,
    ErrorInfo,
    FormatCapability,
    ItemResult,
    ItemStatus,
    ProgressEvent,
    ValidationError,
    error,
    validate_request,
)


class _Observer:
    def __init__(self, callback: Callable[[ProgressEvent], None] | None):
        self.callback = callback
        self.warnings: list[ErrorInfo] = []

    def send(
        self,
        phase: Literal["discovering", "item_started", "item_finished", "finished"],
        items: list[ItemResult],
        total: int | None,
        index: int | None = None,
        item: ItemResult | None = None,
    ) -> None:
        if self.callback is None:
            return
        counts = _counts(items)
        event = ProgressEvent(
            phase,
            index,
            total,
            counts.succeeded + counts.failed,
            counts.succeeded,
            counts.failed,
            counts.cancelled,
            item,
        )
        try:
            self.callback(event)
        except Exception:
            self.callback = None
            self.warnings.append(error(ErrorCode.OBSERVER_FAILED, "observer"))


def _counts(items: list[ItemResult], duplicates: int = 0, ignored: int = 0) -> Counts:
    return Counts(
        len(items),
        sum(i.status == "succeeded" for i in items),
        sum(i.status == "failed" for i in items),
        sum(i.status == "cancelled" for i in items),
        sum(i.artifact is not None for i in items),
        duplicates,
        ignored,
    )


def _validate_destination(options: EffectiveOptions) -> None:
    try:
        if options.output_directory is not None:
            fs.directory_chain(options.output_directory)
        if options.output_path is not None:
            fs.directory_chain(options.output_path.parent)
            # An exact output is only valid for a single explicitly selected file.
            try:
                if stat.S_ISDIR(options.inputs[0].lstat().st_mode):
                    raise fs.fail(ErrorCode.INVALID_DESTINATION, "validation")
            except FileNotFoundError:
                pass  # Discovery will report the missing input.
    except (OSError, fs.OperationError):
        raise fs.fail(ErrorCode.INVALID_DESTINATION, "validation") from None


def _preflight(
    entries: tuple[discovery.Entry, ...],
    options: EffectiveOptions,
) -> tuple[list[Path | None], list[ErrorInfo | None], list[fs.DirectoryChain]]:
    targets = [
        fs.destination_for(entry.source, options) if entry.error is None else None
        for entry in entries
    ]
    groups = Counter(fs.path_key(target) for target in targets if target is not None)
    sources = {fs.path_key(entry.source) for entry in entries}
    identities = {
        entry.fingerprint.identity
        for entry in entries
        if entry.fingerprint is not None and entry.fingerprint.identity is not None
    }
    errors: list[ErrorInfo | None] = []
    parents: list[fs.DirectoryChain] = []
    for entry, target in zip(entries, targets):
        info = entry.error
        parent: fs.DirectoryChain = ()
        if target is not None:
            try:
                parent = fs.target_snapshot(target)
                if fs.path_key(target) in sources or fs.target_identity(target) in identities:
                    info = error(ErrorCode.INPUT_OUTPUT_CONFLICT, "planning")
                elif groups[fs.path_key(target)] > 1:
                    info = error(ErrorCode.TARGET_CONFLICT, "planning")
                elif fs.target_exists(target):
                    info = error(ErrorCode.OUTPUT_EXISTS, "planning")
            except fs.OperationError as exc:
                info = exc.info
            except PermissionError:
                info = error(ErrorCode.OUTPUT_ACCESS_DENIED, "planning")
            except OSError:
                info = error(ErrorCode.INVALID_DESTINATION, "planning")
        errors.append(info)
        parents.append(parent)
    return targets, errors, parents


def _process(
    index: int,
    entry: discovery.Entry,
    destination: Path,
    parent: fs.DirectoryChain,
    options: EffectiveOptions,
    capability: FormatCapability,
    cancellation: CancellationToken,
    operation_id: str,
) -> ItemResult:
    staging: fs.Staging | None = None
    artifact: Artifact | None = None
    info: ErrorInfo | None = None
    warnings: list[ErrorInfo] = []
    facts = imaging.ImageFacts()
    assert entry.fingerprint is not None
    try:
        imaging.check_cancel(cancellation)
        fs.check_chain(parent, ErrorCode.DESTINATION_CHANGED)
        with fs.open_source(entry.source, entry.fingerprint, entry.ancestors) as source:
            staging = fs.Staging.create(destination.parent, parent)
            staging.initialize()
            prepared = imaging.encode(
                source, staging.file, options, capability, facts, cancellation
            )
        staging.check()
        imaging.verify_image(staging.file, options.output_format, prepared)
        size_bytes, digest = fs.digest_file(staging.file)
        fs.check_source(entry.source, entry.fingerprint, entry.ancestors)
        staging.check()
        imaging.check_cancel(cancellation)  # Last cooperative checkpoint before atomic link.
        fs.publish_new(staging, destination)
        # Record the effect immediately, before any fallible readback.
        artifact = Artifact(
            destination,
            options.output_format,
            prepared.width,
            prepared.height,
            size_bytes,
            digest,
            "unverified",
        )
        try:
            if fs.target_identity(destination) != staging.file_identity:
                raise fs.fail(ErrorCode.VERIFICATION_FAILED, "readback")
            imaging.verify_image(destination, options.output_format, prepared)
            if fs.digest_file(destination) != (size_bytes, digest):
                raise fs.fail(ErrorCode.VERIFICATION_FAILED, "readback")
            if fs.target_identity(destination) != staging.file_identity:
                raise fs.fail(ErrorCode.VERIFICATION_FAILED, "readback")
        except Exception:
            raise fs.fail(ErrorCode.PUBLISHED_UNVERIFIED, "readback") from None
        artifact = replace(artifact, publication="verified")
    except fs.OperationError as exc:
        info = exc.info
    except PermissionError:
        info = error(ErrorCode.OUTPUT_ACCESS_DENIED, "prepare")
    except OSError:
        info = error(ErrorCode.WRITE_FAILED, "prepare")
    except Exception:
        info = error(ErrorCode.INTERNAL_ERROR, "prepare")
    finally:
        if staging is not None:
            try:
                clean = staging.cleanup()
            except Exception:
                clean = False
            if not clean:
                warnings.append(error(ErrorCode.TEMP_CLEANUP_FAILED, "cleanup"))
                diagnostics.emit(
                    diagnostics.project(
                        "cleanup_failed",
                        operation_id=operation_id,
                        stage="cleanup",
                        index=index,
                        reason=ErrorCode.TEMP_CLEANUP_FAILED,
                    )
                )
    status: ItemStatus = (
        "succeeded"
        if info is None
        else ("cancelled" if info.code == ErrorCode.CANCELLED else "failed")
    )
    return ItemResult(
        index,
        entry.source,
        destination,
        status,
        facts.source_format,
        facts.source_width,
        facts.source_height,
        entry.fingerprint.size,
        artifact,
        info,
        tuple(warnings),
    )


def convert(
    request: ConversionRequest,
    *,
    cancellation: CancellationToken | None = None,
    on_progress: Callable[[ProgressEvent], None] | None = None,
) -> BatchResult:
    started = monotonic()
    operation_id = uuid4().hex
    diagnostics.emit(diagnostics.project("conversion_started", operation_id=operation_id))
    observer = _Observer(on_progress)
    options: EffectiveOptions | None = None
    items: list[ItemResult] = []

    def finish(result: BatchResult) -> BatchResult:
        observer.send("finished", items, result.counts.total if result.discovery_complete else None)
        result = replace(result, warnings=(*result.warnings, *observer.warnings))
        reason = (
            result.errors[0].code
            if result.errors
            else next((item.error.code for item in result.items if item.error), None)
        )
        diagnostics.emit(
            diagnostics.project(
                "conversion_finished",
                operation_id=operation_id,
                outcome=result.status,
                reason=reason,
                total=result.counts.total,
                succeeded=result.counts.succeeded,
                failed=result.counts.failed,
                cancelled=result.counts.cancelled,
                published=result.counts.published,
                duration_ms=max(0, int((monotonic() - started) * 1000)),
            )
        )
        return result

    try:
        options = validate_request(request, Path.cwd())
        if cancellation is not None and not isinstance(cancellation, CancellationToken):
            raise ValidationError(error(ErrorCode.INVALID_REQUEST, "validation", "cancellation"))
        if on_progress is not None and not callable(on_progress):
            observer.callback = None
            raise ValidationError(error(ErrorCode.INVALID_REQUEST, "validation", "on_progress"))
        _validate_destination(options)
        capability = imaging.get_capabilities().for_format(options.output_format.value)
        if not capability.encoder_available:
            raise ValidationError(
                error(ErrorCode.FORMAT_UNAVAILABLE, "capabilities", "output_format")
            )
    except (ValidationError, fs.OperationError) as exc:
        return finish(BatchResult("rejected", errors=(exc.info,)))
    except Exception:
        return finish(
            BatchResult("failed", options, errors=(error(ErrorCode.INTERNAL_ERROR, "validation"),))
        )

    token = cancellation or CancellationToken()
    manifest: discovery.Manifest | None = None
    try:
        manifest = discovery.build_manifest(
            options.inputs,
            recursive=options.recursive,
            exclude_directory=options.output_directory,
            cancellation=token,
            on_entry=lambda: observer.send("discovering", items, None),
        )
        options = replace(
            options,
            inputs=tuple(fs.normalized(p) for p in options.inputs),
            output_directory=fs.normalized(options.output_directory)
            if options.output_directory is not None
            else None,
            output_path=fs.normalized(options.output_path)
            if options.output_path is not None
            else None,
        )
        if not manifest.complete:
            for index, entry in enumerate(manifest.entries):
                items.append(
                    ItemResult(
                        index,
                        entry.source,
                        None,
                        "failed" if entry.error else "cancelled",
                        source_size_bytes=entry.fingerprint.size if entry.fingerprint else None,
                        error=entry.error or error(ErrorCode.CANCELLED, "discovery"),
                    )
                )
            return finish(
                BatchResult(
                    "cancelled",
                    options,
                    False,
                    tuple(items),
                    warnings=manifest.warnings,
                    counts=_counts(items, manifest.duplicates, manifest.ignored),
                )
            )
        if not manifest.entries:
            return finish(
                BatchResult(
                    "rejected",
                    options,
                    True,
                    errors=(error(ErrorCode.NO_INPUTS, "discovery"),),
                    warnings=manifest.warnings,
                    counts=_counts(items, manifest.duplicates, manifest.ignored),
                )
            )
        targets, planned_errors, parents = _preflight(manifest.entries, options)
        stopped = False
        for index, (entry, destination, planned_error, parent) in enumerate(
            zip(manifest.entries, targets, planned_errors, parents)
        ):
            if planned_error is not None:
                item = ItemResult(
                    index,
                    entry.source,
                    destination,
                    "failed",
                    source_size_bytes=entry.fingerprint.size if entry.fingerprint else None,
                    error=planned_error,
                )
            elif token.is_cancelled():
                stopped = True
                item = ItemResult(
                    index,
                    entry.source,
                    destination,
                    "cancelled",
                    source_size_bytes=entry.fingerprint.size if entry.fingerprint else None,
                    error=error(ErrorCode.CANCELLED, "prepare"),
                )
            else:
                assert destination is not None
                observer.send("item_started", items, len(manifest.entries), index)
                item = _process(
                    index, entry, destination, parent, options, capability, token, operation_id
                )
                if item.status == "cancelled":
                    stopped = True
            items.append(item)
            diagnostics.emit(
                diagnostics.project(
                    "item_finished",
                    operation_id=operation_id,
                    index=index,
                    outcome=item.status,
                    reason=item.error.code if item.error else None,
                    stage=item.error.stage if item.error else "readback",
                    output_format=options.output_format,
                    quality=options.quality,
                    size_bytes=item.artifact.size_bytes if item.artifact else None,
                )
            )
            observer.send("item_finished", items, len(manifest.entries), index, item)
        counts = _counts(items, manifest.duplicates, manifest.ignored)
        status: BatchStatus
        if stopped:
            status = "cancelled"
        elif counts.failed or any(item.warnings for item in items):
            status = "partial" if counts.succeeded or counts.published else "failed"
        else:
            status = "succeeded"
        return finish(
            BatchResult(
                status, options, True, tuple(items), warnings=manifest.warnings, counts=counts
            )
        )
    except Exception:
        # Do not lose a completed discovery snapshot or any known publications
        # when an unexpected orchestration failure prevents the remaining work.
        info = error(ErrorCode.INTERNAL_ERROR, "prepare")
        if manifest is not None:
            for index in range(len(items), len(manifest.entries)):
                entry = manifest.entries[index]
                items.append(
                    ItemResult(
                        index,
                        entry.source,
                        None,
                        "failed",
                        error=entry.error or info,
                        source_size_bytes=entry.fingerprint.size if entry.fingerprint else None,
                    )
                )
        counts = _counts(
            items, manifest.duplicates if manifest else 0, manifest.ignored if manifest else 0
        )
        status = "partial" if counts.succeeded or counts.published else "failed"
        return finish(
            BatchResult(
                status,
                options,
                manifest.complete if manifest else False,
                tuple(items),
                errors=(info,),
                warnings=manifest.warnings if manifest else (),
                counts=counts,
            )
        )
