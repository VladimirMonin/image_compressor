"""Synthetic image-policy discriminators; no application implementation in fixtures."""

import binascii
import struct
import zlib
from pathlib import Path

from PIL import Image

PNG_SAMPLES_16 = {
    0: (0x1234,),
    2: (0x1234, 0x5678, 0x9ABC),
    4: (0x1234, 0x8000),
    6: (0x1234, 0x5678, 0x9ABC, 0x8000),
}
OPAQUE_ALPHA_CASES = ("rgba", "la", "unused_colorkey", "unused_palette_alpha")


def write_alpha_png(path: Path, case: str, *, alpha: int = 255) -> Path:
    options = {}
    if case == "rgba":
        image = Image.new("RGBA", (24, 18), (30, 120, 210, alpha))
    elif case == "la":
        image = Image.new("LA", (24, 18), (120, alpha))
    elif case == "unused_colorkey":
        image = Image.new("RGB", (24, 18), (30, 120, 210))
        options = {"transparency": (255, 0, 0)}
    elif case == "unused_palette_alpha":
        image = Image.new("P", (24, 18), 0)
        image.putpalette([30, 120, 210] + [255, 0, 0] * 255)
        options = {"transparency": 1}
    else:
        raise ValueError("Unknown synthetic case")
    with image:
        image.save(path, **options)
    return path


def write_sample_png(path: Path, *, depth: int, color_type: int) -> Path:
    """Create and independently check PNG IHDR, chunk CRCs and full scanline payload."""
    samples = PNG_SAMPLES_16[color_type]
    if depth == 8:
        samples = tuple(sample >> 8 for sample in samples)
    assert depth in (8, 16)
    raw_pixel = struct.pack(">" + ("H" if depth == 16 else "B") * len(samples), *samples)
    raw = (b"\0" + raw_pixel * 12) * 10
    header = struct.pack(">IIBBBBB", 12, 10, depth, color_type, 0, 0, 0)

    def chunk(tag, data):
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", binascii.crc32(tag + data))
        )

    data = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )
    path.write_bytes(data)
    offset = 8
    tags = []
    while offset < len(data):
        (count,) = struct.unpack(">I", data[offset : offset + 4])
        tag = data[offset + 4 : offset + 8]
        body = data[offset + 8 : offset + 8 + count]
        (crc,) = struct.unpack(">I", data[offset + 8 + count : offset + 12 + count])
        assert crc == binascii.crc32(tag + body)
        if tag == b"IHDR":
            assert struct.unpack(">IIBBBBB", body) == (12, 10, depth, color_type, 0, 0, 0)
        if tag == b"IDAT":
            assert zlib.decompress(body) == raw
        tags.append(tag)
        offset += 12 + count
    assert tags == [b"IHDR", b"IDAT", b"IEND"] and offset == len(data)
    return path


def alpha_extrema(image: Image.Image):
    with image.convert("RGBA") as rgba, rgba.getchannel("A") as alpha:
        return alpha.getextrema()
