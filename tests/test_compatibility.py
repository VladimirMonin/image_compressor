import json
import subprocess
import sys
from pathlib import Path

import pytest

from classes import CompressionError, ImageCompressor
from image_compressor import get_capabilities

from .conftest import assert_image
from .test_cli import REPO, response, run_cli


def test_legacy_real_output_setters_collisions_and_last_result(image_factory, capsys):
    source = image_factory()
    destination = source.with_suffix(".webp")
    compressor = ImageCompressor(quality=80, output_format="webp", max_width=40, max_height=40)
    assert compressor.compress_image(str(source), str(destination)) is None
    assert compressor.last_result.status == "succeeded"
    with assert_image(destination, size=(40, 30)):
        pass
    before = destination.read_bytes()
    with pytest.raises(CompressionError) as exc:
        compressor.compress_image(str(source), str(destination))
    assert exc.value.code == "OUTPUT_EXISTS" and exc.value.result is compressor.last_result
    assert destination.read_bytes() == before
    assert ".webp" in compressor.supported_formats
    compressor.quality = 0
    compressor.output_format = "jpg"
    assert compressor.quality == 0 and compressor.output_format == "JPEG"
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize(
    "kwargs, exception",
    [
        ({"quality": True}, TypeError),
        ({"quality": 1.5}, TypeError),
        ({"quality": -1}, ValueError),
        ({"quality": 101}, ValueError),
        ({"output_format": "PNG"}, ValueError),
        ({"output_format": 7}, TypeError),
        ({"max_width": 3}, TypeError),
        ({"max_width": 0, "max_height": 4}, ValueError),
    ],
)
def test_legacy_constructor_uses_strict_validator(kwargs, exception):
    with pytest.raises(exception):
        ImageCompressor(**kwargs)


def test_legacy_recursive_quoted_input_and_missing(image_factory, tmp_path):
    source = image_factory("input/source.png")
    nested = image_factory("input/sub/nested.png")
    before = {p: p.read_bytes() for p in (source, nested)}
    compressor = ImageCompressor(output_format="WEBP")
    assert compressor.process_directory(str(source.parent)) is None
    assert compressor.last_result.counts.succeeded == 2
    other = image_factory("other.png")
    assert compressor.process_input(f'"{other}"') is None
    with pytest.raises(CompressionError) as exc:
        compressor.process_input(str(tmp_path / "PRIVATE_MISSING_SENTINEL.png"))
    assert exc.value.code == "INPUT_NOT_FOUND"
    assert "PRIVATE_" not in str(exc.value)
    assert all(p.read_bytes() == data for p, data in before.items())


def test_legacy_default_heif_50(image_factory):
    compressor = ImageCompressor()
    assert compressor.quality == 50 and compressor.output_format == "HEIF"
    source = image_factory()
    if get_capabilities().for_format("HEIF").encoder_available:
        compressor.process_input(str(source))
        assert compressor.last_result.status == "succeeded"
        with assert_image(compressor.last_result.items[0].destination, "HEIF"):
            pass
    else:
        with pytest.raises(CompressionError) as exc:
            compressor.process_input(str(source))
        assert exc.value.code == "FORMAT_UNAVAILABLE"


def test_classes_script_forwards_real_cli(image_factory):
    source = image_factory()
    payload = response(run_cli("convert", source, script=REPO / "classes.py"), 0)
    assert payload["status"] == "succeeded"
    with assert_image(Path(payload["result"]["items"][0]["destination"])):
        pass


def test_api_facade_no_qt_parser_input_or_print_in_separate_process(image_factory):
    source = image_factory()
    script = r"""
import builtins, importlib.abc, json, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if (fullname.split('.')[0] in ('PyQt6', 'gui', 'argparse')
                or fullname == 'image_compressor.cli'):
            raise AssertionError('Forbidden dependency')
sys.meta_path.insert(0, Block())
def forbidden(*args, **kwargs):
    raise AssertionError('Forbidden terminal call')
builtins.input = builtins.print = forbidden
import image_compressor
from classes import ImageCompressor
assert image_compressor.imaging._CAPABILITIES is None
result = image_compressor.convert(image_compressor.ConversionRequest([sys.argv[1]]))
compressor = ImageCompressor(output_format='JPEG')
compressor.compress_image(sys.argv[1], sys.argv[2])
assert result.status == compressor.last_result.status == 'succeeded'
sys.stdout.write(json.dumps({'status': result.status}))
"""
    destination = source.with_suffix(".jpg")
    process = subprocess.run(
        [sys.executable, "-c", script, str(source), str(destination)],
        cwd=REPO,
        capture_output=True,
        timeout=40,
    )
    assert process.returncode == 0, process.stderr.decode("utf-8")
    assert json.loads(process.stdout) == {"status": "succeeded"}
    assert process.stderr == b""
    with assert_image(destination, "JPEG"):
        pass


def test_gui_finder_lazy_without_qt(image_factory):
    source = image_factory()
    script = r"""
import importlib.abc, sys
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.startswith('PyQt6'):
            raise AssertionError('Qt imported')
sys.meta_path.insert(0, Block())
import gui
from gui.utils import get_image_files_from_paths
paths = get_image_files_from_paths([sys.argv[1], sys.argv[1]])
assert len(paths) == 1
assert 'gui.main_window' not in sys.modules
"""
    process = subprocess.run(
        [sys.executable, "-c", script, str(source)], cwd=REPO, capture_output=True, timeout=15
    )
    assert process.returncode == 0, process.stderr.decode("utf-8")
    assert not process.stdout and not process.stderr
