from dataclasses import replace

import pytest
from PIL import Image

from image_compressor import ConversionRequest, convert, get_capabilities, imaging

from .conftest import assert_image


@pytest.mark.parametrize("fmt", ["JPEG", "WEBP", "HEIF", "AVIF"])
def test_available_codecs_file_roundtrip(image_factory, fmt):
    capability = get_capabilities().for_format(fmt)
    if not capability.encoder_available:
        assert fmt in ("HEIF", "AVIF")
        assert capability.reason == "CODEC_PROBE_FAILED"
        pytest.skip(f"{fmt}: {capability.reason}")
    assert capability.roundtrip_verified and capability.decoder_registered and capability.provider
    source = image_factory()
    before = source.read_bytes()
    result = convert(ConversionRequest([source], output_format=fmt))
    assert result.status == "succeeded", result
    with assert_image(result.items[0].destination, fmt):
        pass
    target = source.with_name("decoded.jpg")
    decoded = convert(
        ConversionRequest([result.items[0].destination], output_format="JPEG", output_path=target)
    )
    assert decoded.status == "succeeded" and decoded.items[0].source_format == fmt
    assert source.read_bytes() == before


@pytest.mark.parametrize("fmt", ["WEBP", "HEIF", "AVIF"])
def test_alpha_file_roundtrip_or_explicit_refusal(image_factory, fmt):
    capability = get_capabilities().for_format(fmt)
    if not capability.encoder_available:
        assert fmt != "WEBP"
        pytest.skip(f"{fmt}: {capability.reason}")
    source = image_factory(mode="RGBA")
    result = convert(ConversionRequest([source], output_format=fmt))
    if not capability.alpha_verified:
        assert result.items[0].error.code == "IMAGE_MODE_UNSUPPORTED"
    else:
        assert result.status == "succeeded", result
        with Image.open(result.items[0].destination) as image:
            image.load()
            assert image.mode == "RGBA" and image.getchannel("A").getextrema() == (73, 73)


def test_png_decoder_probe_and_encoder_unavailable_seam(image_factory, monkeypatch):
    capabilities = get_capabilities()
    png = capabilities.for_format("PNG")
    assert png.decoder_registered and png.roundtrip_verified and not png.encoder_available
    capabilities = replace(
        capabilities,
        formats=tuple(
            replace(
                item, encoder_available=False, roundtrip_verified=False, reason="CODEC_PROBE_FAILED"
            )
            if item.format == "HEIF"
            else item
            for item in capabilities.formats
        ),
    )
    monkeypatch.setattr(imaging, "get_capabilities", lambda: capabilities)
    source = image_factory()
    result = convert(ConversionRequest([source], output_format="HEIF"))
    assert result.status == "rejected" and result.errors[0].code == "FORMAT_UNAVAILABLE"
    assert result.counts.published == 0
    assert convert(ConversionRequest([source], output_format="WEBP")).status == "succeeded"


def test_no_accidental_avif_provider_override():
    import sys

    capability = get_capabilities().for_format("AVIF")
    if capability.provider == "Pillow":
        assert "pillow_avif" not in sys.modules
