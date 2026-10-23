"""Only synthetic images; all writes live in pytest's disposable roots."""

from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def image_factory(tmp_path):
    def make(name="source.png", size=(80, 60), mode="RGB", color=None, **kwargs):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if color is None:
            color = (32, 120, 210, 73) if mode == "RGBA" else (32, 120, 210)
        with Image.new(mode, size, color) as image:
            image.save(path, **kwargs)
        return path

    return make


def assert_image(path: Path, fmt="WEBP", size=(80, 60)):
    with Image.open(path) as image:
        image.load()
        assert image.format == fmt
        assert image.size == size
        return image.copy()
