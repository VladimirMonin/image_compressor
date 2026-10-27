"""Create-only publication and tracked staging; guarded source deletion has a private owner."""

from __future__ import annotations

import errno
import hashlib
import os
import stat
import tempfile
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import BinaryIO

from .models import (
    EXTENSION_FORMATS,
    OUTPUT_EXTENSIONS,
    EffectiveOptions,
    ErrorCode,
    ErrorInfo,
    Stage,
    error,
)


class OperationError(Exception):
    def __init__(self, info: ErrorInfo):
        super().__init__(info.message)
        self.info = info


def fail(code: ErrorCode, stage: Stage) -> OperationError:
    return OperationError(error(code, stage))


@dataclass(frozen=True)
class Fingerprint:
    device: int
    inode: int
    size: int
    mtime_ns: int
    ctime_ns: int
    # CPython/Windows path stat and descriptor stat can expose different ctime
    # clocks. Snapshot both, rather than drop the ctime guard or compare unlike clocks.
    descriptor_ctime_ns: int | None = field(default=None, compare=False)

    @classmethod
    def from_stat(cls, value: os.stat_result) -> Fingerprint:
        return cls(value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns, value.st_ctime_ns)

    @property
    def identity(self) -> tuple[int, int] | None:
        return (self.device, self.inode) if self.inode else None


DirectoryChain = tuple[tuple[Path, tuple[int, int] | None], ...]


def path_key(path: Path) -> str:
    return os.path.normcase(os.path.abspath(path))


def normalized(path: Path) -> Path:
    return Path(os.path.abspath(path))


def is_link(value: os.stat_result) -> bool:
    return stat.S_ISLNK(value.st_mode) or bool(
        getattr(value, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    )


def directory_chain(path: Path) -> DirectoryChain:
    """Check lexical ancestors before normalizing '..'; never resolve away links."""
    chain: list[tuple[Path, tuple[int, int] | None]] = []
    for part in (*reversed(path.parents), path):
        value = part.lstat()
        if is_link(value):
            raise fail(ErrorCode.UNSAFE_PATH, "read")
        if not stat.S_ISDIR(value.st_mode):
            raise fail(ErrorCode.INPUT_NOT_REGULAR, "read")
        chain.append((part, Fingerprint.from_stat(value).identity))
    return tuple(chain)


def check_chain(chain: DirectoryChain, code: ErrorCode) -> None:
    try:
        for path, identity in chain:
            current = path.lstat()
            if (
                is_link(current)
                or not stat.S_ISDIR(current.st_mode)
                or Fingerprint.from_stat(current).identity != identity
            ):
                raise fail(code, "prepare")
    except OSError:
        raise fail(code, "prepare") from None


def regular_snapshot(path: Path) -> tuple[Fingerprint, DirectoryChain]:
    chain = directory_chain(path.parent)
    value = path.lstat()
    if is_link(value):
        raise fail(ErrorCode.UNSAFE_PATH, "read")
    if not stat.S_ISREG(value.st_mode):
        raise fail(ErrorCode.INPUT_NOT_REGULAR, "read")
    fingerprint = Fingerprint.from_stat(value)
    if os.name == "nt":
        with path.open("rb") as handle:
            descriptor = Fingerprint.from_stat(os.fstat(handle.fileno()))
        if (
            replace(descriptor, ctime_ns=fingerprint.ctime_ns) != fingerprint
            or Fingerprint.from_stat(path.lstat()) != fingerprint
        ):
            raise fail(ErrorCode.SOURCE_CHANGED, "read")
        fingerprint = replace(fingerprint, descriptor_ctime_ns=descriptor.ctime_ns)
    return fingerprint, chain


def check_source(path: Path, expected: Fingerprint, chain: DirectoryChain) -> None:
    check_chain(chain, ErrorCode.SOURCE_CHANGED)
    try:
        current = path.lstat()
        if (
            is_link(current)
            or not stat.S_ISREG(current.st_mode)
            or Fingerprint.from_stat(current) != expected
        ):
            raise fail(ErrorCode.SOURCE_CHANGED, "read")
    except OSError:
        raise fail(ErrorCode.SOURCE_CHANGED, "read") from None


def open_source(path: Path, expected: Fingerprint, chain: DirectoryChain) -> BinaryIO:
    check_source(path, expected, chain)
    try:
        handle = path.open("rb")
    except PermissionError:
        raise fail(ErrorCode.INPUT_ACCESS_DENIED, "read") from None
    except OSError:
        raise fail(ErrorCode.SOURCE_CHANGED, "read") from None
    try:
        value = os.fstat(handle.fileno())
        descriptor_expected = replace(
            expected,
            ctime_ns=expected.descriptor_ctime_ns
            if expected.descriptor_ctime_ns is not None
            else expected.ctime_ns,
        )
        if not stat.S_ISREG(value.st_mode) or Fingerprint.from_stat(value) != descriptor_expected:
            raise fail(ErrorCode.SOURCE_CHANGED, "read")
        check_source(path, expected, chain)
        return handle
    except BaseException:
        handle.close()
        raise


def destination_for(source: Path, options: EffectiveOptions) -> Path:
    if options.output_path is not None:
        return normalized(options.output_path)
    parent = options.output_directory or source.parent
    postfix = (
        options.postfix
        if EXTENSION_FORMATS.get(source.suffix.lower()) == options.output_format.value
        else ""
    )
    return normalized(parent / (source.stem + postfix + OUTPUT_EXTENSIONS[options.output_format]))


def target_snapshot(path: Path) -> DirectoryChain:
    try:
        return directory_chain(path.parent)
    except (OSError, OperationError):
        raise fail(ErrorCode.INVALID_DESTINATION, "validation") from None


def target_exists(path: Path) -> bool:
    try:
        path.lstat()  # Includes dangling symlinks, directories and special entries.
        return True
    except FileNotFoundError:
        return False


def target_identity(path: Path) -> tuple[int, int] | None:
    try:
        return Fingerprint.from_stat(path.lstat()).identity
    except FileNotFoundError:
        return None


@dataclass
class Staging:
    directory: Path
    file: Path
    directory_identity: tuple[int, int] | None
    file_identity: tuple[int, int] | None
    parent_chain: DirectoryChain

    @classmethod
    def create(cls, parent: Path, chain: DirectoryChain) -> Staging:
        check_chain(chain, ErrorCode.DESTINATION_CHANGED)
        try:
            directory = Path(tempfile.mkdtemp(prefix=".ic-", dir=parent))
        except PermissionError:
            raise fail(ErrorCode.OUTPUT_ACCESS_DENIED, "prepare") from None
        except OSError:
            raise fail(ErrorCode.WRITE_FAILED, "prepare") from None
        # Hand ownership to the caller before any more fallible setup. Its finally
        # can then report cleanup failure even after a partially failed acquisition.
        return cls(directory, directory / "payload", None, None, chain)

    def initialize(self) -> None:
        check_chain(self.parent_chain, ErrorCode.DESTINATION_CHANGED)
        directory = self.directory.lstat()
        if is_link(directory) or not stat.S_ISDIR(directory.st_mode):
            raise fail(ErrorCode.DESTINATION_CHANGED, "prepare")
        self.directory_identity = Fingerprint.from_stat(directory).identity
        with self.file.open("xb") as handle:
            self.file_identity = Fingerprint.from_stat(os.fstat(handle.fileno())).identity

    def check(self) -> None:
        check_chain(self.parent_chain, ErrorCode.DESTINATION_CHANGED)
        try:
            directory = self.directory.lstat()
            value = self.file.lstat()
            if (
                is_link(directory)
                or not stat.S_ISDIR(directory.st_mode)
                or Fingerprint.from_stat(directory).identity != self.directory_identity
                or is_link(value)
                or not stat.S_ISREG(value.st_mode)
                or Fingerprint.from_stat(value).identity != self.file_identity
            ):
                raise fail(ErrorCode.DESTINATION_CHANGED, "prepare")
        except OSError:
            raise fail(ErrorCode.DESTINATION_CHANGED, "prepare") from None

    def cleanup(self) -> bool:
        """Remove only our identified file and empty directory. Never recurse."""
        try:
            check_chain(self.parent_chain, ErrorCode.DESTINATION_CHANGED)
            value = self.directory.lstat()
            if (
                is_link(value)
                or not stat.S_ISDIR(value.st_mode)
                or Fingerprint.from_stat(value).identity != self.directory_identity
            ):
                return False
            file_stat: os.stat_result | None
            try:
                file_stat = self.file.lstat()
            except FileNotFoundError:
                file_stat = None
            if file_stat is not None:
                if (
                    self.file_identity is None
                    or is_link(file_stat)
                    or Fingerprint.from_stat(file_stat).identity != self.file_identity
                ):
                    return False
                self.file.unlink()
            self.directory.rmdir()
            return True
        except (OSError, OperationError):
            return False


def digest_stream(handle: BinaryIO) -> tuple[int, str]:
    size = 0
    digest = hashlib.sha256()
    while block := handle.read(1024 * 1024):
        size += len(block)
        digest.update(block)
    return size, digest.hexdigest()


def digest_file(path: Path) -> tuple[int, str]:
    with path.open("rb") as handle:
        return digest_stream(handle)


def publish_new(staging: Staging, destination: Path) -> None:
    try:
        os.link(staging.file, destination)
    except FileExistsError:
        raise fail(ErrorCode.OUTPUT_EXISTS, "publication") from None
    except PermissionError:
        raise fail(ErrorCode.OUTPUT_ACCESS_DENIED, "publication") from None
    except OSError as exc:
        unsupported = {errno.ENOSYS, errno.ENOTSUP, errno.EOPNOTSUPP, errno.EXDEV}
        code = (
            ErrorCode.PUBLICATION_UNSUPPORTED
            if exc.errno in unsupported or getattr(exc, "winerror", None) in (1, 50)
            else ErrorCode.PUBLICATION_FAILED
        )
        raise fail(code, "publication") from None
