import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from .conftest import assert_image
from .image_fixtures import alpha_extrema, write_alpha_png, write_sample_png

REPO = Path(__file__).resolve().parents[1]


def run_cli(*args, cwd=REPO, script=None):
    env = {
        key: os.environ[key]
        for key in ("SYSTEMROOT", "WINDIR", "PATH", "COMSPEC", "TEMP", "TMP")
        if key in os.environ
    }
    env.update(
        PYTHONUTF8="1",
        PYTHONIOENCODING="ascii",
        PYTHONNOUSERSITE="1",
        PYTHONDONTWRITEBYTECODE="1",
        PYTHONPATH=str(REPO),
    )
    command = (
        [sys.executable, str(script)] if script else [sys.executable, "-m", "image_compressor"]
    )
    return subprocess.run(
        [*command, *map(str, args)], cwd=cwd, env=env, capture_output=True, timeout=40
    )


def response(process, expected_exit):
    assert process.returncode == expected_exit, process.stderr.decode("utf-8")
    stdout = process.stdout.decode("utf-8")
    payload = json.loads(stdout)
    assert stdout.endswith("\n") and len(stdout.splitlines()) == 1
    assert payload["schema_version"] == 1
    assert process.stderr and b"Traceback" not in process.stderr
    return payload


def test_cli_single_unicode_space_and_dash(image_factory, tmp_path):
    source = image_factory("Личное имя.png")
    before = source.read_bytes()
    payload = response(run_cli("convert", source, "--json", "--progress"), 0)
    assert payload["status"] == "succeeded"
    (item,) = payload["result"]["items"]
    assert item["source"] == str(source)
    with assert_image(Path(item["destination"])):
        pass
    assert source.read_bytes() == before
    dash = image_factory("-начальный дефис.png")
    payload = response(run_cli("convert", "--", dash.name, cwd=tmp_path), 0)
    assert payload["result"]["counts"]["succeeded"] == 1


def test_cli_recursive_batch_resize_and_partial(image_factory, tmp_path):
    a = image_factory("input/a.png", size=(400, 300))
    b = image_factory("input/sub/b.jpg", size=(20, 10))
    output = tmp_path / "output"
    output.mkdir()
    result = response(
        run_cli(
            "convert",
            a.parent,
            "--recursive",
            "--max-width",
            "192",
            "--max-height",
            "108",
            "--output-dir",
            output,
        ),
        0,
    )
    assert result["result"]["counts"]["succeeded"] == 2
    for destination, size in ((output / "a.webp", (144, 108)), (output / "b.webp", (20, 10))):
        with assert_image(destination, size=size):
            pass
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"CORRUPT_SYNTHETIC_IMAGE")
    partial = response(run_cli("convert", b, bad), 3)
    assert partial["status"] == "partial"
    assert partial["result"]["counts"]["failed"] == 1
    assert partial["result"]["items"][1]["error"]["code"] == "INVALID_IMAGE"


def test_cli_existing_output_and_all_bad(image_factory, tmp_path):
    source = image_factory()
    target = source.with_suffix(".webp")
    target.write_bytes(b"FOREIGN_OUTPUT_SENTINEL")
    payload = response(run_cli("convert", source), 4)
    assert payload["status"] == "failed"
    assert payload["result"]["items"][0]["error"]["code"] == "OUTPUT_EXISTS"
    assert target.read_bytes() == b"FOREIGN_OUTPUT_SENTINEL"
    missing = response(run_cli("convert", tmp_path / "missing.png"), 4)
    assert missing["result"]["counts"]["failed"] == 1


@pytest.mark.parametrize(
    "args, expected_code",
    [
        (["--quality", "101"], "INVALID_QUALITY"),
        (["--quality", "-1"], "INVALID_QUALITY"),
        (["--quality", "PRIVATE_BAD_NUMBER"], "CLI_USAGE"),
        (["--format", "PNG"], "INVALID_FORMAT"),
        # --delete-original is now explicit opt-in; overwrite remains forbidden below.
        (["--overwrite"], "CLI_USAGE"),
        (["--postfix", "PRIVATE_BAD_POSTFIX/"], "INVALID_POSTFIX"),
    ],
)
def test_cli_rejections_safe(image_factory, args, expected_code):
    source = image_factory("PRIVATE_FILENAME_SENTINEL.png")
    process = run_cli("convert", source, *args)
    payload = response(process, 2)
    assert payload["errors"][0]["code"] == expected_code
    assert b"PRIVATE_" not in process.stderr
    assert "PRIVATE_" not in payload["errors"][0]["message"]
    assert not source.with_suffix(".webp").exists()


def test_cli_empty_directory_usage_help_version_and_capabilities(tmp_path):
    payload = response(run_cli("convert", tmp_path), 2)
    assert payload["errors"][0]["code"] == "NO_INPUTS"
    assert response(run_cli(), 2)["errors"][0]["code"] == "CLI_USAGE"
    caps = response(run_cli("capabilities"), 0)
    assert caps["status"] == "succeeded"
    formats = {item["format"]: item for item in caps["result"]["formats"]}
    assert formats["JPEG"]["roundtrip_verified"] and formats["WEBP"]["encoder_available"]
    for option in ("--help", "--version"):
        process = run_cli(option)
        assert process.returncode == 0 and process.stdout and not process.stderr


def test_cli_signal_adapter_real_conversion(image_factory):
    source = image_factory()
    process = run_cli(
        "signal", "convert", source, script=Path(__file__).with_name("cli_harness.py")
    )
    payload = response(process, 130)
    assert payload["status"] == "cancelled"
    assert payload["result"]["counts"]["cancelled"] == 1
    assert payload["result"]["counts"]["published"] == 0
    assert not source.with_suffix(".webp").exists()
    assert not list(source.parent.glob(".ic-*"))
    assert response(run_cli("convert", source), 0)["status"] == "succeeded"


def test_cli_internal_error_and_closed_delivery(image_factory):
    source = image_factory()
    harness = Path(__file__).with_name("cli_harness.py")
    internal = response(run_cli("internal", "convert", source, script=harness), 5)
    assert internal["result"]["items"][0]["error"]["code"] == "INTERNAL_ERROR"
    closed = run_cli("delivery", "convert", source, script=harness)
    assert closed.returncode == 5 and closed.stdout == b"" and b"Traceback" not in closed.stderr
    with assert_image(source.with_suffix(".webp")):
        pass


@pytest.mark.parametrize("alpha", [255, 73])
def test_cli_opaque_and_translucent_png(tmp_path, alpha):
    source = write_alpha_png(tmp_path / "source.png", "rgba", alpha=alpha)
    before = source.read_bytes()
    destination = tmp_path / "result.webp"
    process = run_cli(
        "convert", source, "--output", destination, "--max-width", "12", "--max-height", "9"
    )
    (tmp_path / "cli.stdout").write_bytes(process.stdout)
    (tmp_path / "cli.stderr").write_bytes(process.stderr)
    (tmp_path / "cli.exit").write_text(str(process.returncode), encoding="utf-8")
    result = response(process, 0)
    assert result["status"] == "succeeded"
    assert result["result"]["items"][0]["artifact"]["publication"] == "verified"
    with assert_image(destination, size=(12, 9)) as image:
        assert alpha_extrema(image) == (alpha, alpha)
    assert source.read_bytes() == before and not list(tmp_path.glob(".ic-*"))


@pytest.mark.parametrize("depth", [8, 16])
@pytest.mark.parametrize("color_type", [2, 6])
def test_cli_png_source_precision(tmp_path, depth, color_type):
    source = write_sample_png(tmp_path / "source.png", depth=depth, color_type=color_type)
    before = source.read_bytes()
    destination = tmp_path / "result.webp"
    assert not destination.exists()
    process = run_cli("convert", source, "--output", destination)
    (tmp_path / "cli.stdout").write_bytes(process.stdout)
    (tmp_path / "cli.stderr").write_bytes(process.stderr)
    (tmp_path / "cli.exit").write_text(str(process.returncode), encoding="utf-8")
    result = response(process, 4 if depth == 16 else 0)
    (item,) = result["result"]["items"]
    assert item["source_format"] == "PNG"
    if depth == 16:
        assert result["status"] == "failed" and item["error"]["code"] == "IMAGE_MODE_UNSUPPORTED"
        assert result["result"]["counts"]["published"] == 0 and item["artifact"] is None
        assert not destination.exists()
    else:
        assert result["status"] == "succeeded"
        with assert_image(destination, size=(12, 10)) as image:
            assert alpha_extrema(image) == ((128, 128) if color_type == 6 else (255, 255))
    assert source.read_bytes() == before and not list(tmp_path.glob(".ic-*"))


@pytest.mark.parametrize("delete", [False, True])
def test_cli_explicit_native_deletion_and_false_json_progress(image_factory, delete):
    source = image_factory("PRIVATE_PATH/PRIVATE_SOURCE.png")
    before = source.read_bytes()
    process = run_cli("convert", source, "--progress", "--postfix", "PRIVATE_POSTFIX",
                      *(["--delete-original"] if delete else []))
    result = response(process, 0)["result"]
    assert result["options"]["delete_original"] is delete
    assert result["counts"]["deleted"] == int(delete)
    assert result["items"][0]["source_disposition"] == ("deleted" if delete else "retained")
    assert result["counts"]["succeeded"] == result["counts"]["published"] == 1
    with assert_image(Path(result["items"][0]["destination"])):
        pass
    assert source.exists() is (not delete)
    if not delete:
        assert source.read_bytes() == before
    assert b"stage=observer" in process.stderr and b"PRIVATE_" not in process.stderr
    assert f"deleted={int(delete)}".encode() in process.stderr


def test_cli_native_readonly_refusal_is_not_unsupported_or_silent_false(image_factory):
    source = image_factory()
    before = source.read_bytes()
    source.chmod(stat.S_IREAD)
    try:
        payload = response(run_cli("convert", source, "--delete-original"), 4)
        item = payload["result"]["items"][0]
        assert item["error"]["code"] == "SOURCE_DELETION_FAILED"
        assert item["source_disposition"] == "retained" and item["artifact"] is None
        counts = payload["result"]["counts"]
        assert counts["published"] == counts["deleted"] == 0
        assert source.read_bytes() == before and not source.with_suffix(".webp").exists()
    finally:
        source.chmod(stat.S_IREAD | stat.S_IWRITE)


@pytest.mark.parametrize("mode,code", [("flush", 3), ("unknown", 3), ("close", 5), ("delivery", 5)])
def test_cli_native_useful_output_fault_and_delivery_outcomes(image_factory, tmp_path, mode, code):
    source = image_factory("PRIVATE_SOURCE.png")
    before = source.read_bytes()
    script = r'''
import sys
from image_compressor import cli
from image_compressor import _windows_deletion as native
mode = sys.argv.pop(1)
if mode == 'flush':
    native._api().dll.FlushFileBuffers = lambda raw: 0
elif mode == 'unknown':
    native._confirm_deleted = lambda *args: False
elif mode == 'close':
    original = native.DeletionGuard.close_source
    def failed(self):
        original(self)
        raise RuntimeError('PRIVATE_LIFETIME_EXCEPTION')
    native.DeletionGuard.close_source = failed
elif mode == 'delivery':
    class ClosedOutput:
        def write(self, text): raise BrokenPipeError('PRIVATE_DELIVERY_EXCEPTION')
        def flush(self): pass
        def close(self): pass
    sys.stdout = ClosedOutput()
code = cli.main(sys.argv[1:])
if mode == 'delivery': sys.stdout = sys.__stdout__
raise SystemExit(code)
'''
    process = subprocess.run([sys.executable, "-B", "-c", script, mode, "convert", str(source),
                              "--delete-original", "--progress"],
                             cwd=REPO, capture_output=True, timeout=30)
    (tmp_path / "native-cli.stdout").write_bytes(process.stdout)
    (tmp_path / "native-cli.stderr").write_bytes(process.stderr)
    assert process.returncode == code and b"PRIVATE_" not in process.stderr
    with assert_image(source.with_suffix(".webp")):
        pass
    if mode == "delivery":
        assert process.stdout == b"" and not source.exists()
        assert b"reason=DELIVERY_FAILED" in process.stderr
    else:
        payload = response(process, code)["result"]
        assert payload["counts"]["succeeded"] == payload["counts"]["published"] == 1
        assert payload["counts"]["deleted"] == 0
        item = payload["items"][0]
        assert item["artifact"]["publication"] == "verified" and item["status"] == "succeeded"
        assert item["source_disposition"] == ("retained" if mode == "flush" else "unknown")
        if mode == "flush":
            assert source.read_bytes() == before
        else:
            assert not source.exists()
        if mode == "close":
            assert payload["errors"][0]["code"] == "INTERNAL_ERROR"
