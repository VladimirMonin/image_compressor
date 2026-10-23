"""Synchronous, headless image conversion API (no parser, Qt or import-time probes)."""

from .discovery import discover_inputs
from .imaging import get_capabilities
from .models import (
    Artifact,
    BatchResult,
    CancellationToken,
    Capabilities,
    ConversionRequest,
    Counts,
    DiscoveryResult,
    EffectiveOptions,
    ErrorCode,
    ErrorInfo,
    FormatCapability,
    ItemResult,
    OutputFormat,
    ProgressEvent,
)
from .service import convert

__all__ = [
    "Artifact",
    "BatchResult",
    "CancellationToken",
    "Capabilities",
    "ConversionRequest",
    "Counts",
    "DiscoveryResult",
    "EffectiveOptions",
    "ErrorCode",
    "ErrorInfo",
    "FormatCapability",
    "ItemResult",
    "OutputFormat",
    "ProgressEvent",
    "convert",
    "discover_inputs",
    "get_capabilities",
]
__version__ = "1.0.0"
