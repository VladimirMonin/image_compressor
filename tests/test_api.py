from dataclasses import FrozenInstanceError

import pytest
from PIL import Image

from image_compressor import ConversionRequest, convert
from image_compressor.models import ErrorCode

from .conftest import assert_image


@pytest.mark.parametrize("fmt", ["WEBP", "JPEG"])
@pytest.mark.parametrize("suffix", ["png", "jpg"])
def test_real_single_preserves_source(image_factory, fmt, suffix):
    source = image_factory(f"source.{suffix}")
    before = source.read_bytes()
    result = convert(ConversionRequest([source], output_format=fmt))
    assert result.status == "succeeded", result
    assert result.counts.succeeded == result.counts.published == 1
    (item,) = result.items
    assert item.source_format == ("PNG" if suffix == "png" else "JPEG")
    assert item.artifact.publication == "verified"
    assert item.artifact.sha256 and item.artifact.size_bytes > 0
    with assert_image(item.destination, fmt) as image:
        r, g, b = image.convert("RGB").getpixel((20, 20))
        assert b > g > r
    assert source.read_bytes() == before
    assert list(source.parent.glob(".ic-*")) == []


@pytest.mark.parametrize(
    "overrides, code",
    [
        ({"quality": -1}, "INVALID_QUALITY"),
        ({"quality": 101}, "INVALID_QUALITY"),
        ({"quality": True}, "INVALID_QUALITY"),
        ({"quality": 2.0}, "INVALID_QUALITY"),
        ({"quality": "80"}, "INVALID_QUALITY"),
        ({"output_format": "PNG"}, "INVALID_FORMAT"),
        ({"output_format": "bogus"}, "INVALID_FORMAT"),
        ({"max_width": 1}, "INVALID_DIMENSIONS"),
        ({"max_width": 0, "max_height": 3}, "INVALID_DIMENSIONS"),
        ({"max_width": -1, "max_height": 3}, "INVALID_DIMENSIONS"),
        ({"max_width": True, "max_height": 3}, "INVALID_DIMENSIONS"),
        ({"max_width": 3, "max_height": "4"}, "INVALID_DIMENSIONS"),
        ({"postfix": "../escape"}, "INVALID_POSTFIX"),
        ({"postfix": "x "}, "INVALID_POSTFIX"),
        ({"postfix": "x\n"}, "INVALID_POSTFIX"),
        ({"postfix": "x?"}, "INVALID_POSTFIX"),
        ({"postfix": "x\u0085"}, "INVALID_POSTFIX"),
        ({"recursive": 1}, "INVALID_REQUEST"),
        ({"delete_original": True}, "DESTRUCTIVE_MODE_UNSUPPORTED"),
        ({"delete_original": 0}, "INVALID_REQUEST"),
    ],
)
def test_strict_runtime_rejection_no_effects(image_factory, overrides, code):
    source = image_factory()
    before = source.read_bytes()
    result = convert(ConversionRequest([source], **overrides))
    assert result.status == "rejected"
    assert result.errors[0].code == code
    assert result.items == () and result.counts.published == 0
    assert source.read_bytes() == before
    assert list(source.parent.iterdir()) == [source]


@pytest.mark.parametrize("inputs", [[], "file.png", b"file.png", [b"file.png"], [""], ["\0"], [1]])
def test_invalid_inputs(inputs, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = convert(ConversionRequest(inputs))
    assert result.status == "rejected"
    assert result.errors[0].code == ErrorCode.INVALID_REQUEST
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("quality", [0, 100])
def test_quality_boundaries(image_factory, quality):
    result = convert(ConversionRequest([image_factory()], quality=quality))
    assert result.status == "succeeded"


@pytest.mark.parametrize(
    "size, bounds, expected",
    [
        ((4000, 3000), (1920, 1080), (1440, 1080)),
        ((40, 30), (1920, 1080), (40, 30)),
        ((1, 1000), (10, 10), (1, 10)),
    ],
)
def test_resize_geometry(image_factory, size, bounds, expected):
    source = image_factory(size=size)
    result = convert(ConversionRequest([source], max_width=bounds[0], max_height=bounds[1]))
    assert result.status == "succeeded", result
    with assert_image(result.items[0].destination, size=expected):
        pass


def test_orientation_and_metadata_removed(image_factory):
    exif = Image.Exif()
    exif[274] = 6
    exif[270] = "PRIVATE_METADATA_SENTINEL"
    source = image_factory(
        "oriented.jpg",
        size=(100, 40),
        exif=exif,
        icc_profile=b"PRIVATE_ICC_SENTINEL",
        comment=b"PRIVATE_COMMENT_SENTINEL",
    )
    before = source.read_bytes()
    result = convert(ConversionRequest([source], output_format="JPEG", max_width=20, max_height=40))
    assert result.status == "succeeded", result
    with assert_image(result.items[0].destination, "JPEG", (16, 40)) as image:
        assert not image.getexif()
        assert not image.info.get("icc_profile")
        assert not image.info.get("comment")
    assert b"PRIVATE_" not in result.items[0].destination.read_bytes()
    assert source.read_bytes() == before


def test_white_jpeg_background(image_factory):
    source = image_factory(mode="RGBA", color=(255, 0, 0, 0))
    result = convert(ConversionRequest([source], output_format="JPEG", quality=100))
    assert result.status == "succeeded"
    with assert_image(result.items[0].destination, "JPEG") as image:
        assert min(image.getpixel((0, 0))) >= 250


def test_palette_alpha(image_factory, tmp_path):
    source = tmp_path / "palette.png"
    with Image.new("P", (80, 60), 0) as image:
        image.putpalette([255, 0, 0] + [0, 0, 0] * 255)
        image.save(source, transparency=0)
    result = convert(ConversionRequest([source]))
    assert result.status == "succeeded"
    with assert_image(result.items[0].destination) as image:
        assert image.getchannel("A").getextrema() == (0, 0)


def test_invalid_multiframe_bomb_mode_and_truncated(image_factory, tmp_path, monkeypatch):
    corrupt = tmp_path / "bad.png"
    corrupt.write_bytes(b"NOT_AN_IMAGE")
    assert convert(ConversionRequest([corrupt])).items[0].error.code == "INVALID_IMAGE"
    animated = tmp_path / "animated.webp"
    with Image.new("RGB", (20, 20), "red") as first, Image.new("RGB", (20, 20), "blue") as second:
        first.save(animated, save_all=True, append_images=[second], duration=100, lossless=True)
    assert convert(ConversionRequest([animated])).items[0].error.code == "MULTIFRAME_UNSUPPORTED"
    sixteen = tmp_path / "sixteen.png"
    with Image.new("I;16", (20, 20), 4000) as image:
        image.save(sixteen)
    assert convert(ConversionRequest([sixteen])).items[0].error.code == "IMAGE_MODE_UNSUPPORTED"
    source = image_factory("truncated.jpg", size=(200, 200))
    source.write_bytes(source.read_bytes()[:-100])
    assert convert(ConversionRequest([source])).items[0].error.code == "INVALID_IMAGE"
    bomb = image_factory("bomb.png", size=(20, 20))
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 250)
    assert convert(ConversionRequest([bomb])).items[0].error.code == "IMAGE_LIMIT_EXCEEDED"
    assert not list(tmp_path.glob(".ic-*"))


@pytest.mark.parametrize("mode", ["1", "L", "LA", "P", "RGB", "RGBA", "CMYK"])
@pytest.mark.parametrize("fmt", ["WEBP", "JPEG"])
def test_supported_eight_bit_modes(tmp_path, mode, fmt):
    source = tmp_path / ("mode.jpg" if mode == "CMYK" else "mode.png")
    with Image.new(mode, (12, 10)) as image:
        image.save(source)
    result = convert(ConversionRequest([source], output_format=fmt))
    assert result.status == "succeeded", result
    with assert_image(result.items[0].destination, fmt, (12, 10)):
        pass


def test_supported_suffix_does_not_admit_other_contents(tmp_path):
    source = tmp_path / "actually-bmp.png"
    with Image.new("RGB", (12, 10)) as image:
        image.save(source, format="BMP")
    result = convert(ConversionRequest([source]))
    assert result.items[0].error.code == "INPUT_FORMAT_UNSUPPORTED"
    assert result.counts.published == 0


def test_request_snapshot_defaults_and_immutable(image_factory):
    source = image_factory()
    inputs = [source]
    request = ConversionRequest(inputs)
    inputs.clear()
    result = convert(request)
    assert result.status == "succeeded"
    assert result.options.output_format == "WEBP" and result.options.quality == 80
    assert not result.options.recursive
    with pytest.raises(FrozenInstanceError):
        result.status = "failed"


def test_actual_content_not_suffix(image_factory):
    source = image_factory("content.png")
    renamed = source.with_suffix(".jpg")
    source.rename(renamed)
    result = convert(ConversionRequest([renamed]))
    assert result.status == "succeeded" and result.items[0].source_format == "PNG"


def test_png_color_key_transparency_preserved(tmp_path):
    source = tmp_path / "keyed.png"
    with Image.new("RGB", (12, 10), (32, 120, 210)) as image:
        image.save(source, transparency=(32, 120, 210))
    result = convert(ConversionRequest([source]))
    assert result.status == "succeeded"
    with assert_image(result.items[0].destination, size=(12, 10)) as image:
        assert image.getchannel("A").getextrema() == (0, 0)


def test_orchestration_failure_keeps_completed_manifest(image_factory, monkeypatch):
    from image_compressor import service

    sources = [image_factory(f"{i}.png") for i in range(2)]

    def broken_preflight(*args):
        raise RuntimeError("PRIVATE_ORCHESTRATION_SENTINEL")

    monkeypatch.setattr(service, "_preflight", broken_preflight)
    result = convert(ConversionRequest(sources))
    assert result.status == "failed" and result.discovery_complete
    assert [item.source for item in result.items] == sources
    assert result.counts.total == result.counts.failed == 2
    assert result.counts.published == 0
    assert result.errors[0].code == "INTERNAL_ERROR"
    assert all(item.error.code == "INTERNAL_ERROR" for item in result.items)
