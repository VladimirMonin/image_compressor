"""Pillow owner: lazy providers, real capability probes and explicit raster policy."""

from __future__ import annotations

import binascii
import warnings
from contextlib import ExitStack
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from threading import Lock
from typing import BinaryIO

from PIL import Image, ImageOps, UnidentifiedImageError

from .filesystem import OperationError, fail
from .models import (
    INPUT_EXTENSIONS,
    INPUT_FORMATS,
    CancellationToken,
    Capabilities,
    EffectiveOptions,
    ErrorCode,
    FormatCapability,
    OutputFormat,
)

_CAPABILITIES: Capabilities | None = None
_PROVIDER_LOCK = Lock()
_SUPPORTED_MODES = {"1", "L", "LA", "P", "RGB", "RGBA", "CMYK"}
_METADATA = {"exif", "xmp", "icc_profile", "comment", "description", "XML:com.adobe.xmp"}


def canonical_format(value: str | None) -> str | None:
    return {"JPG": "JPEG", "HEIC": "HEIF"}.get(value or "", value)


def _probe(fmt: str, *, alpha: bool = False) -> bool:
    try:
        mode = "RGBA" if alpha else "RGB"
        with Image.new(mode, (8, 6), (48, 128, 192, 73) if alpha else (48, 128, 192)) as image:
            with BytesIO() as buffer:
                image.save(buffer, format=fmt, quality=80)
                buffer.seek(0)
                with Image.open(buffer) as decoded:
                    decoded.load()
                    return (
                        canonical_format(decoded.format) == fmt
                        and decoded.size == (8, 6)
                        and (
                            not alpha
                            or ("A" in decoded.getbands() and decoded.getextrema()[-1] == (73, 73))
                        )
                    )
    except Exception:
        return False


def get_capabilities() -> Capabilities:
    global _CAPABILITIES
    with _PROVIDER_LOCK:
        if _CAPABILITIES is not None:
            return _CAPABILITIES
        Image.init()
        heif_provider: str | None = None
        try:
            import pillow_heif

            pillow_heif.register_heif_opener()
            heif_provider = "pillow_heif"
        except Exception:
            pass
        # Prefer working built-in AVIF; never import a second provider after success.
        avif_ok = _probe("AVIF")
        avif_provider = "Pillow" if avif_ok else None
        if not avif_ok:
            try:
                import pillow_avif  # noqa: F401

                avif_ok = _probe("AVIF")
                avif_provider = "pillow_avif" if avif_ok else None
            except Exception:
                pass
        formats = []
        for fmt in INPUT_FORMATS:
            provider = (
                heif_provider if fmt == "HEIF" else (avif_provider if fmt == "AVIF" else "Pillow")
            )
            ok = avif_ok if fmt == "AVIF" else _probe(fmt)
            alpha = ok and fmt != "JPEG" and _probe(fmt, alpha=True)
            formats.append(
                FormatCapability(
                    fmt,
                    fmt in Image.OPEN,
                    ok and fmt != "PNG",
                    ok,
                    alpha,
                    provider,
                    None if ok else "CODEC_PROBE_FAILED",
                )
            )
        _CAPABILITIES = Capabilities(INPUT_EXTENSIONS, INPUT_FORMATS, tuple(formats))
        return _CAPABILITIES


@dataclass
class ImageFacts:
    source_format: str | None = None
    source_width: int | None = None
    source_height: int | None = None


@dataclass(frozen=True)
class PreparedImage:
    width: int
    height: int
    alpha: bool  # Actual non-opaque pixels in the prepared/resized raster, not channel presence.


def check_cancel(cancellation: CancellationToken) -> None:
    if cancellation.is_cancelled():
        raise fail(ErrorCode.CANCELLED, "prepare")


def _check_source_precision(source_format: str | None, handle: BinaryIO) -> None:
    if source_format != "PNG":
        return
    # Pillow exposes colour PNG16 as RGB/RGBA before load(), then discards low
    # bits during decode. Inspect the original IHDR through the tracked handle,
    # not the suffix, converted pixels, or Pillow's private tile/rawmode fields.
    position = handle.tell()
    try:
        handle.seek(0)
        header = handle.read(33)  # Signature + fixed-size IHDR + its CRC; bounded I/O.
    finally:
        handle.seek(position)
    if (
        len(header) != 33
        or header[:8] != b"\x89PNG\r\n\x1a\n"
        or header[8:16] != b"\x00\x00\x00\x0dIHDR"
        or binascii.crc32(header[12:29]) != int.from_bytes(header[29:33], "big")
    ):
        raise fail(ErrorCode.INVALID_IMAGE, "decode")
    if header[24] > 8:
        raise fail(ErrorCode.IMAGE_MODE_UNSUPPORTED, "decode")


def _has_transparency(raster: Image.Image) -> bool:
    # Raster/codec channels here are normalized 8-bit channels. Encoders may
    # legitimately omit an entirely opaque A channel, but not real transparency.
    if "A" not in raster.getbands():
        return False
    with raster.getchannel("A") as alpha:
        return alpha.getextrema() != (255, 255)


def fit_size(
    width: int, height: int, max_width: int | None, max_height: int | None
) -> tuple[int, int]:
    if max_width is None or max_height is None:
        return width, height
    ratio = min(1, max_width / width, max_height / height)
    return max(1, int(width * ratio)), max(1, int(height * ratio))


def encode(
    handle: BinaryIO,
    staging_path: Path,
    options: EffectiveOptions,
    capability: FormatCapability,
    facts: ImageFacts,
    cancellation: CancellationToken,
) -> PreparedImage:
    # Warning-to-error is local; do not alter Pillow's global bomb/truncation limits.
    with warnings.catch_warnings(), ExitStack() as stack:
        warnings.simplefilter("ignore")  # Never forward raw metadata/codec warning text.
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            source = stack.enter_context(Image.open(handle))
            facts.source_format = canonical_format(source.format)
            facts.source_width, facts.source_height = source.size
            if facts.source_format not in INPUT_FORMATS:
                raise fail(ErrorCode.INPUT_FORMAT_UNSUPPORTED, "decode")
            if getattr(source, "n_frames", 1) > 1:
                raise fail(ErrorCode.MULTIFRAME_UNSUPPORTED, "decode")
            if source.mode not in _SUPPORTED_MODES:
                raise fail(ErrorCode.IMAGE_MODE_UNSUPPORTED, "decode")
            _check_source_precision(facts.source_format, handle)
            source.load()
            oriented = stack.enter_context(ImageOps.exif_transpose(source))
            check_cancel(cancellation)
            alpha_bearing = "A" in oriented.getbands() or "transparency" in oriented.info
            converted = stack.enter_context(oriented.convert("RGBA" if alpha_bearing else "RGB"))
            if alpha_bearing and options.output_format == OutputFormat.JPEG:
                raster = stack.enter_context(Image.new("RGB", converted.size, "white"))
                alpha = stack.enter_context(converted.getchannel("A"))
                raster.paste(converted, mask=alpha)
            else:
                # A brand-new raster, not a copied info/getexif object: metadata is not inherited.
                raster = stack.enter_context(Image.new(converted.mode, converted.size))
                raster.paste(converted)
            size = fit_size(*raster.size, options.max_width, options.max_height)
            if raster.size != size:
                raster = stack.enter_context(raster.resize(size, Image.Resampling.LANCZOS))
            transparent = _has_transparency(raster)
            if transparent and not capability.alpha_verified:
                raise fail(ErrorCode.IMAGE_MODE_UNSUPPORTED, "decode")
            if not transparent and "A" in raster.getbands():
                raster = stack.enter_context(raster.convert("RGB"))
            raster.info.clear()
            check_cancel(cancellation)
        except (Image.DecompressionBombWarning, Image.DecompressionBombError):
            raise fail(ErrorCode.IMAGE_LIMIT_EXCEEDED, "decode") from None
        except OperationError:
            raise
        except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError):
            raise fail(ErrorCode.INVALID_IMAGE, "decode") from None
        try:
            raster.save(staging_path, format=options.output_format.value, quality=options.quality)
        except Exception:
            raise fail(ErrorCode.ENCODE_FAILED, "encode") from None
        check_cancel(cancellation)
        return PreparedImage(*size, transparent)


def verify_image(path: Path, fmt: OutputFormat, prepared: PreparedImage) -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        warnings.simplefilter("error", Image.DecompressionBombWarning)
        try:
            with Image.open(path) as decoded:
                decoded.load()
                if (
                    canonical_format(decoded.format) != fmt.value
                    or decoded.size != (prepared.width, prepared.height)
                    or _has_transparency(decoded) != prepared.alpha
                    or any(decoded.info.get(key) for key in _METADATA)
                    or bool(decoded.getexif())
                ):
                    raise fail(ErrorCode.VERIFICATION_FAILED, "verification")
        except OperationError:
            raise
        except Exception:
            raise fail(ErrorCode.VERIFICATION_FAILED, "verification") from None
