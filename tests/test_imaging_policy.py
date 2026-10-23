"""R1/R2 regressions at the real API + Pillow + staging/readback boundary."""

from dataclasses import replace

import pytest
from PIL import Image, PngImagePlugin

from image_compressor import ConversionRequest, convert, get_capabilities, imaging
from image_compressor.filesystem import OperationError
from image_compressor.models import OutputFormat

from .conftest import assert_image
from .image_fixtures import (
    OPAQUE_ALPHA_CASES,
    PNG_SAMPLES_16,
    alpha_extrema,
    write_alpha_png,
    write_sample_png,
)


def available_formats():
    formats = [item.format for item in get_capabilities().formats if item.encoder_available]
    assert "WEBP" in formats and "JPEG" in formats
    return formats


@pytest.mark.parametrize("case", OPAQUE_ALPHA_CASES)
def test_opaque_alpha_bearing_png_is_supported(tmp_path, case):
    source = write_alpha_png(tmp_path / "source.png", case)
    before = source.read_bytes()
    with Image.open(source) as image:
        assert alpha_extrema(image) == (255, 255)
    for fmt in available_formats():
        result = convert(ConversionRequest([source], output_format=fmt))
        assert result.status == "succeeded", result
        assert result.counts.published == result.counts.succeeded == 1
        assert result.items[0].artifact.publication == "verified"
        with assert_image(result.items[0].destination, fmt, (24, 18)) as image:
            assert alpha_extrema(image) == (255, 255)
        assert source.read_bytes() == before
        assert not list(tmp_path.glob(".ic-*"))


@pytest.mark.parametrize("alpha", [0, 73, 255])
def test_rgba_semantic_transparency_survives_resize(tmp_path, alpha):
    source = write_alpha_png(tmp_path / "source.png", "rgba", alpha=alpha)
    before = source.read_bytes()
    for fmt in available_formats():
        result = convert(ConversionRequest([source], output_format=fmt, max_width=12, max_height=9))
        assert result.status == "succeeded", result
        with assert_image(result.items[0].destination, fmt, (12, 9)) as image:
            assert alpha_extrema(image) == ((255, 255) if fmt == "JPEG" else (alpha, alpha))
        assert source.read_bytes() == before


def test_transparency_is_measured_after_resizing(tmp_path):
    source = tmp_path / "sparse-alpha.png"
    with Image.new("RGBA", (64, 64), (30, 120, 210, 255)) as image:
        image.putpixel((0, 0), (30, 120, 210, 0))
        assert alpha_extrema(image) == (0, 255)
        with image.resize((1, 1), Image.Resampling.LANCZOS) as resized:
            assert alpha_extrema(resized) == (255, 255)
        image.save(source)
    result = convert(ConversionRequest([source], max_width=1, max_height=1))
    assert result.status == "succeeded", result
    with assert_image(result.items[0].destination, size=(1, 1)) as image:
        assert alpha_extrema(image) == (255, 255)


def test_alpha_capability_is_required_only_for_actual_prepared_transparency(tmp_path, monkeypatch):
    capabilities = get_capabilities()
    limited = replace(
        capabilities,
        formats=tuple(
            replace(item, alpha_verified=False) if item.format == "WEBP" else item
            for item in capabilities.formats
        ),
    )
    monkeypatch.setattr(imaging, "get_capabilities", lambda: limited)
    opaque = write_alpha_png(tmp_path / "opaque.png", "rgba")
    transparent = write_alpha_png(tmp_path / "transparent.png", "rgba", alpha=73)
    assert convert(ConversionRequest([opaque])).status == "succeeded"
    result = convert(ConversionRequest([transparent]))
    assert result.items[0].error.code == "IMAGE_MODE_UNSUPPORTED"
    assert result.counts.published == 0 and not transparent.with_suffix(".webp").exists()


@pytest.mark.parametrize("mutation", ["drop", "make_opaque", "introduce"])
def test_verification_still_rejects_changed_transparency(tmp_path, monkeypatch, mutation):
    source = write_alpha_png(
        tmp_path / "source.png", "rgba", alpha=255 if mutation == "introduce" else 73
    )
    before = source.read_bytes()
    get_capabilities()
    original = Image.Image.save

    def wrong_transparency(image, *args, **kwargs):
        with image.convert("RGB" if mutation == "drop" else "RGBA") as altered:
            if mutation != "drop":
                altered.putalpha(73 if mutation == "introduce" else 255)
            return original(altered, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "save", wrong_transparency)
    result = convert(ConversionRequest([source]))
    assert result.status == "failed" and result.items[0].error.code == "VERIFICATION_FAILED"
    assert result.counts.published == 0 and result.items[0].artifact is None
    assert source.read_bytes() == before and not list(tmp_path.glob(".ic-*"))


def test_verifier_requires_real_transparency_not_only_an_alpha_band(tmp_path):
    for fmt in available_formats():
        if fmt == "JPEG":
            continue
        path = tmp_path / ("opaque." + {"WEBP": "webp", "HEIF": "heic", "AVIF": "avif"}[fmt])
        with Image.new("RGBA", (24, 18), (30, 120, 210, 255)) as image:
            image.save(path, format=fmt)
        # Some codecs keep opaque A and others legitimately omit it. Neither
        # representation satisfies a prepared image that actually needed transparency.
        with pytest.raises(OperationError) as exc:
            imaging.verify_image(path, OutputFormat(fmt), imaging.PreparedImage(24, 18, True))
        assert exc.value.info.code == "VERIFICATION_FAILED"


@pytest.mark.parametrize("color_type", [0, 2, 4, 6])
def test_png_original_16bit_precision_rejected_before_decode(tmp_path, color_type, monkeypatch):
    source = write_sample_png(tmp_path / "sixteen.png", depth=16, color_type=color_type)
    before = source.read_bytes()
    # Confirm the discriminator: Pillow exposes 16-bit colour inputs as RGB/RGBA,
    # whereas grayscale remains I;16. The original samples are independently checked.
    with Image.open(source) as image:
        assert image.format == "PNG" and image.size == (12, 10)
        if color_type in (2, 4, 6):
            assert image.mode in ("RGB", "RGBA")
    get_capabilities()
    original = PngImagePlugin.PngImageFile.load
    decodes = []

    def source_load(image, *args, **kwargs):
        if getattr(image.fp, "name", None) == str(source):
            decodes.append(True)
        return original(image, *args, **kwargs)

    monkeypatch.setattr(PngImagePlugin.PngImageFile, "load", source_load)
    result = convert(ConversionRequest([source]))
    assert result.status == "failed", result
    assert result.items[0].error.code == "IMAGE_MODE_UNSUPPORTED"
    assert result.items[0].error.stage == "decode"
    assert result.counts.published == 0 and result.items[0].artifact is None
    assert not decodes  # Rejection precedes Pillow's irreversible sample downconversion.
    assert not source.with_suffix(".webp").exists() and not list(tmp_path.glob(".ic-*"))
    assert source.read_bytes() == before


@pytest.mark.parametrize("color_type", [0, 2, 4, 6])
def test_matching_8bit_png_positive_controls(tmp_path, color_type):
    source = write_sample_png(tmp_path / "eight.png", depth=8, color_type=color_type)
    before = source.read_bytes()
    with Image.open(source) as image:
        image.load()
        samples = tuple(sample >> 8 for sample in PNG_SAMPLES_16[color_type])
        assert image.getpixel((0, 0)) == (samples[0] if color_type == 0 else samples)
    result = convert(ConversionRequest([source]))
    assert result.status == "succeeded", result
    with assert_image(result.items[0].destination, size=(12, 10)) as image:
        assert alpha_extrema(image) == ((128, 128) if color_type in (4, 6) else (255, 255))
    assert source.read_bytes() == before


def test_png_precision_uses_actual_container_not_extension(tmp_path):
    source = write_sample_png(tmp_path / "sixteen.jpg", depth=16, color_type=2)
    result = convert(ConversionRequest([source], output_format="JPEG"))
    assert result.status == "failed" and result.items[0].source_format == "PNG"
    assert result.items[0].error.code == "IMAGE_MODE_UNSUPPORTED"
    assert result.counts.published == 0
