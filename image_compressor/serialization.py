"""Code-first JSON projection for the closed public DTO set; never repr arbitrary objects."""

from __future__ import annotations

from dataclasses import fields
from enum import Enum
from pathlib import Path
from typing import TypeAlias

from .models import (
    Artifact,
    BatchResult,
    Capabilities,
    Counts,
    EffectiveOptions,
    ErrorInfo,
    FormatCapability,
    ItemResult,
)

JSONValue: TypeAlias = "None | bool | int | str | list[JSONValue] | dict[str, JSONValue]"
_PUBLIC = (
    Artifact,
    BatchResult,
    Capabilities,
    Counts,
    EffectiveOptions,
    ErrorInfo,
    FormatCapability,
    ItemResult,
)


def to_json(value: object) -> JSONValue:
    if value is None:
        return None
    if isinstance(value, Enum):
        return to_json(value.value)
    if isinstance(value, (bool, int, str)):
        return value
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [to_json(item) for item in value]
    if isinstance(value, _PUBLIC):
        return {field.name: to_json(getattr(value, field.name)) for field in fields(value)}
    raise TypeError("Unsupported JSON value.")


def envelope(
    command: str | None,
    status: str,
    result: BatchResult | Capabilities | None,
    errors: tuple[ErrorInfo, ...] = (),
) -> dict[str, JSONValue]:
    return {
        "schema_version": 1,
        "command": command,
        "status": status,
        "result": to_json(result),
        "errors": to_json(errors),
    }
