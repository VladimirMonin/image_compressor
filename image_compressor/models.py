"""Immutable application contract and shared, strict runtime validation (no I/O)."""

from __future__ import annotations

import os
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from threading import Event
from typing import Literal


class OutputFormat(str, Enum):
    JPEG = "JPEG"
    WEBP = "WEBP"
    HEIF = "HEIF"
    AVIF = "AVIF"


INPUT_EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp", ".heic", ".heif", ".avif")
INPUT_FORMATS = ("JPEG", "PNG", "WEBP", "HEIF", "AVIF")
OUTPUT_EXTENSIONS = {
    OutputFormat.JPEG: ".jpg",
    OutputFormat.WEBP: ".webp",
    OutputFormat.HEIF: ".heic",
    OutputFormat.AVIF: ".avif",
}
EXTENSION_FORMATS = {
    ".jpg": "JPEG",
    ".jpeg": "JPEG",
    ".png": "PNG",
    ".webp": "WEBP",
    ".heic": "HEIF",
    ".heif": "HEIF",
    ".avif": "AVIF",
}


class ErrorCode(str, Enum):
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_FORMAT = "INVALID_FORMAT"
    INVALID_QUALITY = "INVALID_QUALITY"
    INVALID_DIMENSIONS = "INVALID_DIMENSIONS"
    INVALID_POSTFIX = "INVALID_POSTFIX"
    INVALID_DESTINATION = "INVALID_DESTINATION"
    FORMAT_UNAVAILABLE = "FORMAT_UNAVAILABLE"
    DESTRUCTIVE_MODE_UNSUPPORTED = "DESTRUCTIVE_MODE_UNSUPPORTED"
    NO_INPUTS = "NO_INPUTS"
    INPUT_NOT_FOUND = "INPUT_NOT_FOUND"
    INPUT_NOT_REGULAR = "INPUT_NOT_REGULAR"
    UNSUPPORTED_INPUT_EXTENSION = "UNSUPPORTED_INPUT_EXTENSION"
    UNSAFE_PATH = "UNSAFE_PATH"
    INPUT_ACCESS_DENIED = "INPUT_ACCESS_DENIED"
    DIRECTORY_READ_FAILED = "DIRECTORY_READ_FAILED"
    SOURCE_CHANGED = "SOURCE_CHANGED"
    INVALID_IMAGE = "INVALID_IMAGE"
    INPUT_FORMAT_UNSUPPORTED = "INPUT_FORMAT_UNSUPPORTED"
    MULTIFRAME_UNSUPPORTED = "MULTIFRAME_UNSUPPORTED"
    IMAGE_MODE_UNSUPPORTED = "IMAGE_MODE_UNSUPPORTED"
    IMAGE_LIMIT_EXCEEDED = "IMAGE_LIMIT_EXCEEDED"
    ENCODE_FAILED = "ENCODE_FAILED"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    INPUT_OUTPUT_CONFLICT = "INPUT_OUTPUT_CONFLICT"
    TARGET_CONFLICT = "TARGET_CONFLICT"
    OUTPUT_EXISTS = "OUTPUT_EXISTS"
    OUTPUT_ACCESS_DENIED = "OUTPUT_ACCESS_DENIED"
    WRITE_FAILED = "WRITE_FAILED"
    DESTINATION_CHANGED = "DESTINATION_CHANGED"
    PUBLICATION_UNSUPPORTED = "PUBLICATION_UNSUPPORTED"
    PUBLICATION_FAILED = "PUBLICATION_FAILED"
    PUBLISHED_UNVERIFIED = "PUBLISHED_UNVERIFIED"
    TEMP_CLEANUP_FAILED = "TEMP_CLEANUP_FAILED"
    CANCELLED = "CANCELLED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    OBSERVER_FAILED = "OBSERVER_FAILED"
    CLI_USAGE = "CLI_USAGE"
    SIGNAL_UNAVAILABLE = "SIGNAL_UNAVAILABLE"
    DELIVERY_FAILED = "DELIVERY_FAILED"


Stage = Literal[
    "validation",
    "capabilities",
    "discovery",
    "planning",
    "read",
    "decode",
    "encode",
    "verification",
    "prepare",
    "publication",
    "readback",
    "cleanup",
    "observer",
    "cli",
]
Field = Literal[
    "inputs",
    "output_format",
    "quality",
    "max_width",
    "max_height",
    "recursive",
    "output_directory",
    "output_path",
    "postfix",
    "delete_original",
    "cancellation",
    "on_progress",
]
BatchStatus = Literal["rejected", "succeeded", "failed", "partial", "cancelled"]
ItemStatus = Literal["succeeded", "failed", "cancelled"]
PathInput = str | os.PathLike[str]


@dataclass(frozen=True)
class ErrorInfo:
    code: ErrorCode
    message: str
    stage: Stage
    field: Field | None = None


def error(code: ErrorCode, stage: Stage, field: Field | None = None) -> ErrorInfo:
    # Only enum-derived fixed messages; never interpolate OS/codec exceptions or paths.
    message = code.value.replace("_", " ").capitalize() + "."
    if code == ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED:
        message = "Deleting or replacing originals is not supported; disable delete_original."
    elif code == ErrorCode.CLI_USAGE:
        message = "Invalid command line; use --help."
    return ErrorInfo(code, message, stage, field)


class ValidationError(Exception):
    def __init__(self, info: ErrorInfo, *, type_error: bool = False):
        super().__init__(info.message)
        self.info = info
        self.type_error = type_error


def invalid(code: ErrorCode, field: Field, *, type_error: bool = False) -> ValidationError:
    return ValidationError(error(code, "validation", field), type_error=type_error)


def validate_format(value: object) -> OutputFormat:
    if not isinstance(value, str):
        raise invalid(ErrorCode.INVALID_FORMAT, "output_format", type_error=True)
    name = {"JPG": "JPEG", "HEIC": "HEIF"}.get(value.upper(), value.upper())
    try:
        return OutputFormat(name)
    except ValueError:
        raise invalid(ErrorCode.INVALID_FORMAT, "output_format") from None


def validate_quality(value: object) -> int:
    if type(value) is not int:
        raise invalid(ErrorCode.INVALID_QUALITY, "quality", type_error=True)
    if not 0 <= value <= 100:
        raise invalid(ErrorCode.INVALID_QUALITY, "quality")
    return value


def validate_dimensions(width: object, height: object) -> tuple[int | None, int | None]:
    if width is None and height is None:
        return None, None
    dimensions: tuple[tuple[object, Field], ...] = ((width, "max_width"), (height, "max_height"))
    for value, field in dimensions:
        if type(value) is not int:
            raise invalid(ErrorCode.INVALID_DIMENSIONS, field, type_error=True)
        if value <= 0:
            raise invalid(ErrorCode.INVALID_DIMENSIONS, field)
    assert isinstance(width, int) and isinstance(height, int)
    return width, height


def validate_postfix(value: object) -> str:
    if not isinstance(value, str):
        raise invalid(ErrorCode.INVALID_POSTFIX, "postfix", type_error=True)
    if any(unicodedata.category(c) == "Cc" or c in '/\\<>:"|?*' for c in value) or value.endswith(
        (".", " ")
    ):
        raise invalid(ErrorCode.INVALID_POSTFIX, "postfix")
    return value


def path_value(value: object, field: Field = "inputs") -> Path:
    try:
        if not isinstance(value, (str, os.PathLike)):
            raise TypeError
        text = os.fspath(value)
        if not isinstance(text, str) or not text or "\0" in text:
            raise ValueError
        return Path(text)
    except (TypeError, ValueError):
        code = ErrorCode.INVALID_REQUEST if field == "inputs" else ErrorCode.INVALID_DESTINATION
        raise invalid(code, field) from None


@dataclass(frozen=True)
class ConversionRequest:
    inputs: Sequence[PathInput]
    output_format: str = "WEBP"
    quality: int = 80
    max_width: int | None = None
    max_height: int | None = None
    recursive: bool = False
    output_directory: PathInput | None = None
    output_path: PathInput | None = None
    postfix: str = "_compressed"
    delete_original: bool = False

    def __post_init__(self) -> None:
        # Invalid scalars remain invalid for convert(); valid sequences are snapshotted.
        if isinstance(self.inputs, Sequence) and not isinstance(self.inputs, (str, bytes)):
            object.__setattr__(self, "inputs", tuple(self.inputs))


@dataclass(frozen=True)
class EffectiveOptions:
    inputs: tuple[Path, ...]
    output_format: OutputFormat
    quality: int
    max_width: int | None
    max_height: int | None
    recursive: bool
    output_directory: Path | None
    output_path: Path | None
    postfix: str
    delete_original: bool = False


def validate_request(request: object, cwd: Path) -> EffectiveOptions:
    if not isinstance(request, ConversionRequest):
        raise invalid(ErrorCode.INVALID_REQUEST, "inputs", type_error=True)
    for name in ("delete_original", "recursive"):
        if type(getattr(request, name)) is not bool:
            raise invalid(ErrorCode.INVALID_REQUEST, name, type_error=True)
    if request.delete_original:
        raise invalid(ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED, "delete_original")
    fmt = validate_format(request.output_format)
    quality = validate_quality(request.quality)
    width, height = validate_dimensions(request.max_width, request.max_height)
    postfix = validate_postfix(request.postfix)
    if (
        not isinstance(request.inputs, Sequence)
        or isinstance(request.inputs, (str, bytes))
        or not request.inputs
    ):
        raise invalid(ErrorCode.INVALID_REQUEST, "inputs")
    # Keep lexical '..' until filesystem has checked the unhidden ancestor chain.
    inputs = tuple(cwd / path_value(p) for p in request.inputs)
    directory = (
        cwd / path_value(request.output_directory, "output_directory")
        if request.output_directory is not None
        else None
    )
    destination = (
        cwd / path_value(request.output_path, "output_path")
        if request.output_path is not None
        else None
    )
    if directory is not None and destination is not None:
        raise invalid(ErrorCode.INVALID_DESTINATION, "output_path")
    if destination is not None:
        if len(inputs) != 1 or EXTENSION_FORMATS.get(destination.suffix.lower()) != fmt.value:
            raise invalid(ErrorCode.INVALID_DESTINATION, "output_path")
    return EffectiveOptions(
        inputs, fmt, quality, width, height, request.recursive, directory, destination, postfix
    )


class CancellationToken:
    """One operation's cooperative stop request; deliberately has no reset()."""

    def __init__(self) -> None:
        self._event = Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True)
class Artifact:
    path: Path
    format: OutputFormat
    width: int
    height: int
    size_bytes: int
    sha256: str
    publication: Literal["verified", "unverified"]


@dataclass(frozen=True)
class ItemResult:
    index: int
    source: Path
    destination: Path | None
    status: ItemStatus
    source_format: str | None = None
    source_width: int | None = None
    source_height: int | None = None
    source_size_bytes: int | None = None
    artifact: Artifact | None = None
    error: ErrorInfo | None = None
    warnings: tuple[ErrorInfo, ...] = ()
    source_disposition: Literal["retained"] = "retained"


@dataclass(frozen=True)
class Counts:
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    cancelled: int = 0
    published: int = 0
    duplicates: int = 0
    ignored: int = 0


@dataclass(frozen=True)
class BatchResult:
    status: BatchStatus
    options: EffectiveOptions | None = None
    discovery_complete: bool = False
    items: tuple[ItemResult, ...] = ()
    errors: tuple[ErrorInfo, ...] = ()
    warnings: tuple[ErrorInfo, ...] = ()
    counts: Counts = Counts()


@dataclass(frozen=True)
class ProgressEvent:
    phase: Literal["discovering", "item_started", "item_finished", "finished"]
    index: int | None
    total: int | None
    processed: int
    succeeded: int
    failed: int
    cancelled: int
    item: ItemResult | None = None


@dataclass(frozen=True)
class DiscoveryIssue:
    source: Path
    error: ErrorInfo


@dataclass(frozen=True)
class DiscoveryResult:
    paths: tuple[Path, ...] = ()
    issues: tuple[DiscoveryIssue, ...] = ()
    discovery_complete: bool = True
    duplicates: int = 0
    ignored: int = 0
    errors: tuple[ErrorInfo, ...] = ()
    warnings: tuple[ErrorInfo, ...] = ()


@dataclass(frozen=True)
class FormatCapability:
    format: str
    decoder_registered: bool
    encoder_available: bool
    roundtrip_verified: bool
    alpha_verified: bool
    provider: str | None
    reason: str | None


@dataclass(frozen=True)
class Capabilities:
    input_extensions: tuple[str, ...]
    input_formats: tuple[str, ...]
    formats: tuple[FormatCapability, ...]

    def for_format(self, fmt: str) -> FormatCapability:
        return next(item for item in self.formats if item.format == fmt)
