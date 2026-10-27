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

from . import _windows_deletion as deletion
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
        sum(i.source_disposition == "deleted" for i in items),
    )


def _validate_destination(options: EffectiveOptions) -> None:
    try:
        if options.delete_original:
            for target in (options.output_directory, options.output_path):
                if target is not None:
                    try:
                        deletion.validate_location(target)
                    except fs.OperationError:
                        return  # Per-item refusal in preflight, without unsafe traversal.
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
                if options.delete_original:
                    for selected in (options.output_directory, options.output_path):
                        if selected is not None:
                            deletion.validate_location(selected)  # Check before collapsing '..'.
                    deletion.validate_location(entry.source)
                    deletion.validate_location(target)
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
    guard: deletion.DeletionGuard | None = None
    cleanup_attempted = False
    clean = True
    artifact: Artifact | None = None
    info: ErrorInfo | None = None
    disposition: Literal["retained", "deleted", "unknown"] = "retained"
    warnings: list[ErrorInfo] = []
    facts = imaging.ImageFacts()
    assert entry.fingerprint is not None

    def cleanup() -> bool:
        assert staging is not None
        try:
            cleaned = staging.cleanup()
        except Exception:
            cleaned = False
        if not cleaned:
            warnings.append(error(ErrorCode.TEMP_CLEANUP_FAILED, "cleanup"))
            diagnostics.emit(diagnostics.project(
                "cleanup_failed", operation_id=operation_id, stage="cleanup", index=index,
                reason=ErrorCode.TEMP_CLEANUP_FAILED,
            ))
        return cleaned

    try:
        imaging.check_cancel(cancellation)
        fs.check_chain(parent, ErrorCode.DESTINATION_CHANGED)
        if options.delete_original:
            guard = deletion.DeletionGuard.acquire(
                entry.source, entry.fingerprint, entry.ancestors, destination, parent
            )
        source_handle = (guard.source_stream() if guard is not None else
                         fs.open_source(entry.source, entry.fingerprint, entry.ancestors))
        with source_handle as source:
            initial_digest = fs.digest_stream(source) if guard is not None else None
            if guard is not None:
                source.seek(0)
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
        # Record the effect immediately, before any fallible cleanup/readback.
        artifact = Artifact(destination, options.output_format, prepared.width, prepared.height,
                            size_bytes, digest, "unverified")
        if guard is not None:
            cleanup_attempted = True  # Never retry cleanup after a changed/foreign staging.
            clean = cleanup()  # Must precede final deny-delete lock: these are hardlinks.
            try:
                guard.lock_final(destination, staging.file_identity)
                with guard.final_stream() as final_stream:
                    imaging.verify_image(final_stream, options.output_format, prepared)
                with guard.final_stream() as final_stream:
                    if fs.digest_stream(final_stream) != (size_bytes, digest):
                        raise fs.fail(ErrorCode.VERIFICATION_FAILED, "readback")
            except (OSError, fs.OperationError):
                raise fs.fail(ErrorCode.PUBLISHED_UNVERIFIED, "readback") from None
        else:
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
        if guard is not None:
            try:
                guard.flush_final()
                fs.check_chain(parent, ErrorCode.DESTINATION_CHANGED)
                guard.check_source()
                with guard.source_stream() as source:
                    if fs.digest_stream(source) != initial_digest:
                        raise fs.fail(ErrorCode.SOURCE_CHANGED, "source_deletion")
                # All source duplicates are closed before the only destructive call.
                if cancellation.is_cancelled():
                    warnings.append(error(ErrorCode.CANCELLED, "source_deletion"))
                elif not clean:
                    warnings.append(error(ErrorCode.SOURCE_DELETION_SKIPPED, "source_deletion"))
                else:
                    guard.accept_disposition()
                    disposition = "unknown"
                    guard.close_source()  # Keep final/namespace locked through confirmation.
                    if guard.confirm_deleted():
                        disposition = "deleted"
            except fs.OperationError as exc:
                warnings.append(replace(exc.info, stage="source_deletion"))
            except OSError:
                warnings.append(error(ErrorCode.SOURCE_DELETION_FAILED, "source_deletion"))
    except fs.OperationError as exc:
        info = exc.info
    except PermissionError:
        info = error(ErrorCode.OUTPUT_ACCESS_DENIED, "prepare")
    except OSError:
        info = error(ErrorCode.WRITE_FAILED, "prepare")
    except Exception:
        info = error(ErrorCode.INTERNAL_ERROR, "prepare")
    finally:
        if staging is not None and not cleanup_attempted:
            cleanup()
        if guard is not None:
            if guard.disposition_accepted and disposition != "deleted":
                disposition = "unknown"
                warnings.append(error(ErrorCode.SOURCE_DELETION_UNCONFIRMED, "source_deletion"))
            try:
                guard.close()
            except Exception:
                # Not swallowed: surface fatal lifetime failure with the known artifact/outcome.
                info = error(ErrorCode.INTERNAL_ERROR, "source_deletion")
    if guard is not None and artifact is not None and artifact.publication == "verified" and info:
        warnings.append(info)
        info = None  # Conversion success is independent of deletion/close success.
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
        disposition,
    )


def _build_manifest(
    options: EffectiveOptions, token: CancellationToken, observer: _Observer,
    items: list[ItemResult],
) -> discovery.Manifest:
    inputs = options.inputs
    refused: dict[str, discovery.Entry] = {}
    if options.delete_original:
        safe: list[Path] = []
        for path in inputs:
            try:
                deletion.validate_location(path)
                safe.append(path)
            except fs.OperationError as exc:
                refused.setdefault(fs.path_key(path), discovery.Entry(path, error=exc.info))
        inputs = tuple(safe)
    manifest = discovery.build_manifest(
        inputs, recursive=options.recursive, exclude_directory=options.output_directory,
        cancellation=token, on_entry=lambda: observer.send("discovering", items, None),
    )
    if refused:
        manifest = replace(manifest, entries=(*manifest.entries, *refused.values()))
    return manifest


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
            else next(
                (item.error.code for item in result.items if item.error),
                next((warning.code for item in result.items for warning in item.warnings), None),
            )
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
                deleted=result.counts.deleted,
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
        if options.delete_original and not deletion.available():
            raise ValidationError(error(ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED,
                                        "validation", "delete_original"))
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
        manifest = _build_manifest(options, token, observer, items)
        lexical_options = options  # Destructive admission must not hide a reparse/dot ancestor.
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
        targets, planned_errors, parents = _preflight(
            manifest.entries, lexical_options if options.delete_original else options
        )
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
                if item.status == "cancelled" or any(
                    warning.code == ErrorCode.CANCELLED for warning in item.warnings
                ):
                    stopped = True
            items.append(item)
            diagnostics.emit(
                diagnostics.project(
                    "item_finished",
                    operation_id=operation_id,
                    index=index,
                    outcome=item.status,
                    reason=item.error.code if item.error else
                           (item.warnings[0].code if item.warnings else None),
                    stage=item.error.stage if item.error else
                          (item.warnings[0].stage if item.warnings else "readback"),
                    source_disposition=item.source_disposition,
                    deleted=int(item.source_disposition == "deleted"),
                    output_format=options.output_format,
                    quality=options.quality,
                    size_bytes=item.artifact.size_bytes if item.artifact else None,
                )
            )
            observer.send("item_finished", items, len(manifest.entries), index, item)
            if options.delete_original and any(
                problem.code == ErrorCode.INTERNAL_ERROR
                for problem in (*item.warnings, *((item.error,) if item.error else ()))
            ):
                raise RuntimeError("Fatal guarded lifetime failure.")
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
