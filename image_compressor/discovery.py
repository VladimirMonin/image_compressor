"""Deterministic, first-wins local discovery. No codecs and no writes."""

from __future__ import annotations

import os
import stat
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import filesystem as fs
from .models import (
    INPUT_EXTENSIONS,
    CancellationToken,
    ConversionRequest,
    DiscoveryIssue,
    DiscoveryResult,
    ErrorCode,
    ErrorInfo,
    PathInput,
    ValidationError,
    error,
    validate_request,
)


@dataclass(frozen=True)
class Entry:
    source: Path
    fingerprint: fs.Fingerprint | None = None
    ancestors: fs.DirectoryChain = ()
    error: ErrorInfo | None = None


@dataclass(frozen=True)
class Manifest:
    entries: tuple[Entry, ...]
    complete: bool
    duplicates: int
    ignored: int
    warnings: tuple[ErrorInfo, ...] = ()

    def public(self) -> DiscoveryResult:
        return DiscoveryResult(
            tuple(entry.source for entry in self.entries if entry.error is None),
            tuple(
                DiscoveryIssue(entry.source, entry.error)
                for entry in self.entries
                if entry.error is not None
            ),
            self.complete,
            self.duplicates,
            self.ignored,
            warnings=self.warnings,
        )


def _read_error(exc: OSError) -> ErrorInfo:
    code = (
        ErrorCode.INPUT_NOT_FOUND
        if isinstance(exc, FileNotFoundError)
        else ErrorCode.INPUT_ACCESS_DENIED
        if isinstance(exc, PermissionError)
        else ErrorCode.INPUT_NOT_REGULAR
    )
    return error(code, "discovery")


@contextmanager
def _directory_children(path: Path) -> Iterator[Iterator[Path]]:
    with os.scandir(path) as children:
        yield (path / child.name for child in children)


def build_manifest(
    inputs: tuple[Path, ...],
    *,
    recursive: bool,
    exclude_directory: Path | None,
    cancellation: CancellationToken,
    on_entry: Callable[[], None] | None = None,
) -> Manifest:
    entries: list[Entry] = []
    seen_paths: set[str] = set()
    seen_identities: set[tuple[int, int]] = set()
    duplicates = 0
    ignored = 0
    complete = True
    warnings: list[ErrorInfo] = []

    def checkpoint() -> bool:
        nonlocal complete
        if on_entry is not None:
            on_entry()
        if cancellation.is_cancelled():
            complete = False
            return False
        return True

    def add(candidate: Entry) -> None:
        nonlocal duplicates
        key = fs.path_key(candidate.source)
        identity = candidate.fingerprint.identity if candidate.fingerprint else None
        if key in seen_paths or (identity is not None and identity in seen_identities):
            duplicates += 1
            return
        seen_paths.add(key)
        if identity is not None:
            seen_identities.add(identity)
        entries.append(candidate)

    def file_entry(path: Path) -> Entry:
        try:
            fingerprint, ancestors = fs.regular_snapshot(path)
            return Entry(fs.normalized(path), fingerprint, ancestors)
        except fs.OperationError as exc:
            return Entry(fs.normalized(path), error=exc.info)
        except OSError as exc:
            return Entry(fs.normalized(path), error=_read_error(exc))

    for root in inputs:
        if not checkpoint():
            break
        root_entries: list[Entry] = []
        try:
            fs.directory_chain(root.parent)
            value = root.lstat()
            if fs.is_link(value):
                add(Entry(fs.normalized(root), error=error(ErrorCode.UNSAFE_PATH, "discovery")))
                continue
            if stat.S_ISREG(value.st_mode):
                if root.suffix.lower() not in INPUT_EXTENSIONS:
                    add(
                        Entry(
                            fs.normalized(root),
                            error=error(ErrorCode.UNSUPPORTED_INPUT_EXTENSION, "discovery"),
                        )
                    )
                else:
                    add(file_entry(root))
                continue
            if not stat.S_ISDIR(value.st_mode):
                add(
                    Entry(
                        fs.normalized(root), error=error(ErrorCode.INPUT_NOT_REGULAR, "discovery")
                    )
                )
                continue
        except fs.OperationError as exc:
            add(Entry(fs.normalized(root), error=exc.info))
            continue
        except OSError as exc:
            add(Entry(fs.normalized(root), error=_read_error(exc)))
            continue

        exclude: str | None = None
        if exclude_directory is not None:
            root_key, output_key = fs.path_key(root), fs.path_key(exclude_directory)
            try:
                if (
                    root_key != output_key
                    and os.path.commonpath((root_key, output_key)) == root_key
                ):
                    exclude = output_key
            except ValueError:  # Different drives.
                pass

        def walk(directory: Path) -> None:
            nonlocal ignored
            try:
                # Stream names so cancellation is observed between actual scandir
                # entries, not only after an unbounded list/sort has completed.
                with _directory_children(directory) as children:
                    for child in children:
                        if not checkpoint():
                            return
                        if exclude is not None and fs.path_key(child) == exclude:
                            continue
                        try:
                            child_stat = child.lstat()
                            if fs.is_link(child_stat):
                                ignored += 1
                                warnings.append(error(ErrorCode.UNSAFE_PATH, "discovery"))
                            elif stat.S_ISDIR(child_stat.st_mode):
                                if recursive:
                                    walk(child)
                                    if not complete:
                                        return
                            elif stat.S_ISREG(child_stat.st_mode):
                                if child.suffix.lower() in INPUT_EXTENSIONS:
                                    root_entries.append(file_entry(child))
                                else:
                                    ignored += 1
                            else:
                                ignored += 1
                                warnings.append(error(ErrorCode.INPUT_NOT_REGULAR, "discovery"))
                        except OSError as exc:
                            root_entries.append(Entry(fs.normalized(child), error=_read_error(exc)))
            except OSError:
                root_entries.append(
                    Entry(
                        fs.normalized(directory),
                        error=error(ErrorCode.DIRECTORY_READ_FAILED, "discovery"),
                    )
                )

        walk(root)
        root_absolute = fs.normalized(root)
        for candidate in sorted(
            root_entries,
            key=lambda entry: (
                str(entry.source.relative_to(root_absolute)).casefold(),
                str(entry.source.relative_to(root_absolute)),
            ),
        ):
            add(candidate)
        if not complete:
            break
    return Manifest(tuple(entries), complete, duplicates, ignored, tuple(warnings))


def discover_inputs(
    inputs: Sequence[PathInput],
    *,
    recursive: bool = False,
    exclude_directory: PathInput | None = None,
    cancellation: CancellationToken | None = None,
) -> DiscoveryResult:
    try:
        if cancellation is not None and not isinstance(cancellation, CancellationToken):
            return DiscoveryResult(
                errors=(error(ErrorCode.INVALID_REQUEST, "validation", "cancellation"),)
            )
        options = validate_request(
            ConversionRequest(inputs, recursive=recursive, output_directory=exclude_directory),
            Path.cwd(),
        )
        return build_manifest(
            options.inputs,
            recursive=options.recursive,
            exclude_directory=options.output_directory,
            cancellation=cancellation or CancellationToken(),
        ).public()
    except ValidationError as exc:
        return DiscoveryResult(errors=(exc.info,))
    except Exception:
        return DiscoveryResult(
            discovery_complete=False, errors=(error(ErrorCode.INTERNAL_ERROR, "discovery"),)
        )
