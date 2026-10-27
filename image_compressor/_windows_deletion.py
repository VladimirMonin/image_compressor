"""Private Windows local-NTFS handles. No deletion by path, fallback, or Qt dependency.

Sharing protects ordinary opens/renames, not pre-existing writable mappings or
privileged/raw-volume interference. Disposition acceptance is NOT confirmed removal.
"""

from __future__ import annotations

import ctypes
import os
import stat
from dataclasses import dataclass, replace
from pathlib import Path, PureWindowsPath
from typing import BinaryIO

from . import filesystem as fs
from .models import ErrorCode

_READ = 0x80000000
_WRITE = 0x40000000
_DELETE = 0x00010000
_ATTRIBUTES = 0x80
_LIST_DIRECTORY = 0x0001
_SHARE_READ = 1
_SHARE_WRITE = 2
_SHARE_DELETE = 4
_OPEN_EXISTING = 3
_BACKUP = 0x02000000
_NO_REPARSE = 0x00200000
_REPARSE = 0x400
_READONLY = 1
_INVALID = ctypes.c_void_p(-1).value
_API: _Api | None = None


class _Basic(ctypes.Structure):
    _fields_ = [(name, ctypes.c_int64) for name in
                ("creation", "access", "write", "change")] + [("attributes", ctypes.c_uint32)]


class _Standard(ctypes.Structure):
    _fields_ = [("allocation", ctypes.c_int64), ("size", ctypes.c_int64),
                ("links", ctypes.c_uint32), ("pending", ctypes.c_ubyte),
                ("directory", ctypes.c_ubyte)]


class _Tag(ctypes.Structure):
    _fields_ = [("attributes", ctypes.c_uint32), ("tag", ctypes.c_uint32)]


class _FileId(ctypes.Structure):
    _fields_ = [("volume", ctypes.c_uint64), ("identifier", ctypes.c_ubyte * 16)]


class _Disposition(ctypes.Structure):
    _fields_ = [("delete", ctypes.c_ubyte)]  # Windows BOOLEAN, not BOOL/pointer.


class NativeLifetimeError(RuntimeError):
    """Unexpected ownership/close failure; callers must preserve known effects."""


class _Api:
    def __init__(self) -> None:
        dll = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = ctypes.c_void_p
        dword = ctypes.c_uint32
        pointer = ctypes.c_void_p
        declarations = {
            "CreateFileW": (
                [ctypes.c_wchar_p, dword, dword, pointer, dword, dword, handle], handle),
            "GetFileInformationByHandleEx": ([handle, ctypes.c_int, pointer, dword], ctypes.c_int),
            "GetFileType": ([handle], dword),
            "GetVolumeInformationByHandleW": (
                [handle, ctypes.c_wchar_p, dword, pointer, pointer, pointer,
                 ctypes.c_wchar_p, dword], ctypes.c_int),
            "GetDriveTypeW": ([ctypes.c_wchar_p], dword),
            "GetCurrentProcess": ([], handle),
            "DuplicateHandle": ([handle, handle, handle, pointer, dword, ctypes.c_int, dword],
                                ctypes.c_int),
            "SetFileInformationByHandle": ([handle, ctypes.c_int, pointer, dword], ctypes.c_int),
            "FlushFileBuffers": ([handle], ctypes.c_int),
            "CloseHandle": ([handle], ctypes.c_int),
        }
        for name, (arguments, result) in declarations.items():
            function = getattr(dll, name)
            function.argtypes = arguments
            function.restype = result
        self.dll = dll


def _api() -> _Api:
    global _API
    if _API is None:
        _API = _Api()
    return _API


def available() -> bool:
    if os.name != "nt":
        return False
    try:
        _api()
    except (AttributeError, OSError):
        return False
    return True


def validate_location(path: Path) -> None:
    """Reject unsafe namespaces lexically, and mapped/removable drives before traversal."""
    windows = PureWindowsPath(path)
    drive = windows.drive
    reserved = {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
    reserved.update(f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10))
    if (len(drive) != 2 or drive[1] != ":" or not drive[0].isascii()
            or not drive[0].isalpha() or windows.root != "\\"
            or any(part in (".", "..") or part.endswith((".", " ")) or ":" in part
                   or part.split(".")[0].upper() in reserved for part in windows.parts[1:])):
        raise fs.fail(ErrorCode.UNSAFE_PATH, "source_deletion")
    if _api().dll.GetDriveTypeW(windows.anchor) != 3:  # DRIVE_FIXED only.
        raise fs.fail(ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED, "source_deletion")


def _os_error() -> OSError:
    return ctypes.WinError(ctypes.get_last_error())


def _query(raw: int, kind: int, result: ctypes.Structure) -> None:
    if not _api().dll.GetFileInformationByHandleEx(raw, kind, ctypes.byref(result),
                                                 ctypes.sizeof(result)):
        raise _os_error()


@dataclass(frozen=True)
class Snapshot:
    identity: tuple[int, int]
    size: int
    links: int
    pending: bool
    directory: bool
    attributes: int
    creation: int
    write: int
    change: int


def _snapshot(raw: int) -> Snapshot:
    basic, standard, tag, identity = _Basic(), _Standard(), _Tag(), _FileId()
    _query(raw, 0, basic)
    _query(raw, 1, standard)
    _query(raw, 9, tag)
    _query(raw, 18, identity)
    if _api().dll.GetFileType(raw) != 1:  # FILE_TYPE_DISK
        raise fs.fail(ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED, "source_deletion")
    file_id = (int(identity.volume), int.from_bytes(bytes(identity.identifier), "little"))
    if not all(file_id):
        raise fs.fail(ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED, "source_deletion")
    return Snapshot(file_id, int(standard.size), int(standard.links), bool(standard.pending),
                    bool(standard.directory), int(tag.attributes), int(basic.creation),
                    int(basic.write), int(basic.change))


class _Handle:
    def __init__(self, raw: int):
        self.raw: int | None = raw

    @classmethod
    def open(cls, path: Path, access: int, share: int, *, directory: bool = False) -> _Handle:
        # Only validated ordinary drive paths reach this private primitive.
        raw = _api().dll.CreateFileW("\\\\?\\" + str(path), access, share, None,
                                    _OPEN_EXISTING, _NO_REPARSE | (_BACKUP if directory else 0),
                                    None)
        if raw is None or raw == _INVALID:
            raise _os_error()
        return cls(int(raw))

    def value(self) -> int:
        if self.raw is None:
            raise NativeLifetimeError("Native handle is already closed.")
        return self.raw

    def close(self) -> None:
        if self.raw is None:
            return
        raw, self.raw = self.raw, None  # Never close/retry a possibly recycled handle value.
        if not _api().dll.CloseHandle(raw):
            raise NativeLifetimeError("Native handle close failed.")

    def stream(self) -> BinaryIO:
        import msvcrt

        duplicate = ctypes.c_void_p()
        dll = _api().dll
        process = dll.GetCurrentProcess()
        if not dll.DuplicateHandle(process, self.value(), process, ctypes.byref(duplicate),
                                   0, False, 2):  # DUPLICATE_SAME_ACCESS
            raise _os_error()
        raw = duplicate.value
        if raw is None:
            raise NativeLifetimeError("Native duplicate ownership failed.")
        try:
            descriptor = msvcrt.open_osfhandle(raw, os.O_RDONLY | os.O_BINARY)
        except BaseException:
            _Handle(raw).close()
            raise
        try:
            stream = os.fdopen(descriptor, "rb")
        except BaseException:
            os.close(descriptor)  # CRT owns the duplicate now, not _Handle.
            raise
        try:
            stream.seek(0)  # DuplicateHandle shares the object's file position.
        except BaseException:
            stream.close()
            raise
        return stream

    def snapshot(self) -> Snapshot:
        return _snapshot(self.value())

    def require_ntfs(self) -> None:
        name = ctypes.create_unicode_buffer(32)
        if not _api().dll.GetVolumeInformationByHandleW(self.value(), None, 0, None, None,
                                                       None, name, len(name)):
            raise _os_error()
        if name.value != "NTFS":
            raise fs.fail(ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED, "source_deletion")


def _check_regular(snapshot: Snapshot) -> None:
    if snapshot.attributes & _REPARSE:
        raise fs.fail(ErrorCode.UNSAFE_PATH, "source_deletion")
    if snapshot.directory or snapshot.pending:
        raise fs.fail(ErrorCode.SOURCE_DELETION_FAILED, "source_deletion")


def _confirm_deleted(path: Path, original: tuple[int, int]) -> bool:
    try:
        handle = _Handle.open(path, _ATTRIBUTES, _SHARE_READ | _SHARE_WRITE | _SHARE_DELETE,
                              directory=True)
    except OSError as exc:
        return getattr(exc, "winerror", None) == 2  # FILE_NOT_FOUND, NOT PATH_NOT_FOUND/access.
    try:
        return handle.snapshot().identity != original  # Never touch a foreign replacement.
    except (OSError, fs.OperationError):
        return False
    finally:
        handle.close()


class DeletionGuard:
    """One item owns its namespace, source and final handles through confirmation."""

    def __init__(self, source: Path, expected: fs.Fingerprint, ancestors: fs.DirectoryChain):
        self.path = source
        self.expected = expected
        self.ancestors = ancestors
        self.directories: list[_Handle] = []
        self.source: _Handle | None = None
        self.final: _Handle | None = None
        self.initial: Snapshot | None = None
        self.disposition_accepted = False

    @classmethod
    def acquire(cls, source: Path, expected: fs.Fingerprint, ancestors: fs.DirectoryChain,
                destination: Path, parents: fs.DirectoryChain) -> DeletionGuard:
        guard = cls(source, expected, ancestors)
        try:
            validate_location(source)
            validate_location(destination)
            unique = {fs.path_key(path): (path, identity) for path, identity in
                      (*ancestors, *parents)}
            for path, identity in sorted(unique.values(), key=lambda item: len(item[0].parts)):
                handle = _Handle.open(path, _LIST_DIRECTORY | _ATTRIBUTES,
                                      _SHARE_READ | _SHARE_WRITE,
                                      directory=True)
                guard.directories.append(handle)  # Own before any fallible query.
                snapshot = handle.snapshot()
                if (not snapshot.directory or snapshot.pending
                        or snapshot.attributes & _REPARSE or snapshot.identity != identity):
                    raise fs.fail(ErrorCode.SOURCE_CHANGED, "source_deletion")
                handle.require_ntfs()
            fs.check_chain(ancestors, ErrorCode.SOURCE_CHANGED)
            fs.check_chain(parents, ErrorCode.DESTINATION_CHANGED)
            guard.source = _Handle.open(source, _READ | _DELETE, 0)
            snapshot = guard.source.snapshot()
            _check_regular(snapshot)
            guard.source.require_ntfs()
            if snapshot.links != 1:
                raise fs.fail(ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED, "source_deletion")
            if snapshot.attributes & _READONLY:
                raise fs.fail(ErrorCode.SOURCE_DELETION_FAILED, "source_deletion")
            if (snapshot.identity != expected.identity or snapshot.size != expected.size
                    or (snapshot.write - 116444736000000000) * 100 != expected.mtime_ns):
                raise fs.fail(ErrorCode.SOURCE_CHANGED, "source_deletion")
            with guard.source.stream() as stream:
                current = fs.Fingerprint.from_stat(os.fstat(stream.fileno()))
                descriptor_expected = replace(expected, ctime_ns=expected.descriptor_ctime_ns
                                              if expected.descriptor_ctime_ns is not None
                                              else expected.ctime_ns)
                if (not stat.S_ISREG(os.fstat(stream.fileno()).st_mode)
                        or current != descriptor_expected):
                    raise fs.fail(ErrorCode.SOURCE_CHANGED, "source_deletion")
            fs.check_source(source, expected, ancestors)
            guard.initial = snapshot
            return guard
        except BaseException as exc:
            guard.close()
            if isinstance(exc, OSError):
                raise fs.fail(ErrorCode.SOURCE_DELETION_FAILED, "source_deletion") from None
            raise

    def source_stream(self) -> BinaryIO:
        if self.source is None:
            raise NativeLifetimeError("Source ownership is missing.")
        return self.source.stream()

    def check_source(self) -> None:
        if self.source is None or self.initial is None:
            raise NativeLifetimeError("Source ownership is missing.")
        fs.check_source(self.path, self.expected, self.ancestors)
        snapshot = self.source.snapshot()
        if snapshot != self.initial or snapshot.links != 1:
            raise fs.fail(ErrorCode.SOURCE_CHANGED, "source_deletion")

    def lock_final(self, destination: Path, expected: tuple[int, int] | None) -> None:
        self.final = _Handle.open(destination, _READ | _WRITE, _SHARE_READ)
        snapshot = self.final.snapshot()
        _check_regular(snapshot)
        if snapshot.identity != expected or snapshot.identity == self.expected.identity:
            raise fs.fail(ErrorCode.VERIFICATION_FAILED, "readback")

    def final_stream(self) -> BinaryIO:
        if self.final is None:
            raise NativeLifetimeError("Final ownership is missing.")
        return self.final.stream()

    def flush_final(self) -> None:
        if self.final is None:
            raise NativeLifetimeError("Final ownership is missing.")
        if not _api().dll.FlushFileBuffers(self.final.value()):
            raise fs.fail(ErrorCode.SOURCE_DELETION_FAILED, "source_deletion")

    def accept_disposition(self) -> None:
        if self.source is None or self.disposition_accepted:
            raise NativeLifetimeError("Invalid disposition transition.")
        disposition = _Disposition(1)
        if not _api().dll.SetFileInformationByHandle(self.source.value(), 4,
                                                    ctypes.byref(disposition),
                                                    ctypes.sizeof(disposition)):
            raise fs.fail(ErrorCode.SOURCE_DELETION_FAILED, "source_deletion")
        self.disposition_accepted = True  # Immediately, before close/confirmation can fail.

    def close_source(self) -> None:
        if self.source is not None:
            self.source.close()

    def confirm_deleted(self) -> bool:
        if (not self.disposition_accepted or self.source is None
                or self.source.raw is not None or self.initial is None):
            raise NativeLifetimeError("Invalid confirmation transition.")
        return _confirm_deleted(self.path, self.initial.identity)

    def close(self) -> None:
        failure: NativeLifetimeError | None = None
        handles = [self.source, self.final, *reversed(self.directories)]
        for handle in handles:
            if handle is not None:
                try:
                    handle.close()
                except NativeLifetimeError as exc:
                    failure = failure or exc
        if failure is not None:
            raise failure
