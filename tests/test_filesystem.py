import errno
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest
from PIL import Image

from image_compressor import ConversionRequest, convert, get_capabilities, imaging
from image_compressor import filesystem as fs

from .conftest import assert_image


def test_existing_output_repeat_and_empty_postfix(image_factory):
    source = image_factory("source.webp")
    before = source.read_bytes()
    same = convert(ConversionRequest([source], postfix=""))
    assert same.items[0].error.code == "INPUT_OUTPUT_CONFLICT"
    result = convert(ConversionRequest([source]))
    destination = source.with_name("source_compressed.webp")
    assert result.status == "succeeded"
    existing = destination.read_bytes()
    again = convert(ConversionRequest([source]))
    assert again.items[0].error.code == "OUTPUT_EXISTS"
    assert source.read_bytes() == before and destination.read_bytes() == existing
    exact = convert(ConversionRequest([source], output_path=source))
    assert exact.items[0].error.code == "INPUT_OUTPUT_CONFLICT"


def test_collision_groups_and_other_input_preserved(image_factory, tmp_path):
    a = image_factory("a.png")
    b = image_factory("a.jpg", color=(210, 32, 120))
    c = image_factory("ok.png")
    before = {p: p.read_bytes() for p in (a, b, c)}
    result = convert(ConversionRequest([a, b, c]))
    assert result.status == "partial"
    assert [i.error.code if i.error else None for i in result.items] == [
        "TARGET_CONFLICT",
        "TARGET_CONFLICT",
        None,
    ]
    assert result.counts.total == 3 and result.counts.succeeded == result.counts.published == 1
    assert all(p.read_bytes() == data for p, data in before.items())
    input_target = image_factory("other.webp")
    other_source = image_factory("other.png")
    snapshot = input_target.read_bytes()
    result = convert(ConversionRequest([other_source, input_target]))
    assert result.items[0].error.code == "INPUT_OUTPUT_CONFLICT"
    assert result.items[1].status == "succeeded"
    assert input_target.read_bytes() == snapshot


def test_jpeg_heif_alias_naming(image_factory):
    jpeg = image_factory("photo.JPEG")
    result = convert(ConversionRequest([jpeg], output_format="jpg", postfix="_small"))
    assert result.status == "succeeded"
    assert result.items[0].destination.name == "photo_small.jpg"
    options = result.options
    from dataclasses import replace

    assert (
        fs.destination_for(
            jpeg.with_suffix(".HEIF"), replace(options, output_format=imaging.OutputFormat.HEIF)
        ).name
        == "photo_small.heic"
    )


@pytest.mark.parametrize(
    "option", ["bad_suffix", "multiple", "directory", "missing_parent", "both"]
)
def test_exact_output_validation(image_factory, tmp_path, option):
    source = image_factory()
    kwargs = {"output_path": tmp_path / "exact.webp"}
    inputs = [source]
    if option == "bad_suffix":
        kwargs["output_path"] = tmp_path / "wrong.jpg"
    elif option == "multiple":
        inputs.append(source)
    elif option == "directory":
        inputs = [tmp_path]
    elif option == "missing_parent":
        kwargs["output_path"] = tmp_path / "missing" / "exact.webp"
    elif option == "both":
        kwargs["output_directory"] = tmp_path
    result = convert(ConversionRequest(inputs, **kwargs))
    assert result.status == "rejected" and result.errors[0].code == "INVALID_DESTINATION"
    assert list(tmp_path.iterdir()) == [source]


def test_output_hardlink_alias_of_input(image_factory):
    source = image_factory()
    target = source.with_suffix(".webp")
    os.link(source, target)
    before = target.read_bytes()
    result = convert(ConversionRequest([source]))
    assert result.items[0].error.code == "INPUT_OUTPUT_CONFLICT"
    assert target.read_bytes() == source.read_bytes() == before


def test_foreign_destination_race_uses_real_link(image_factory, monkeypatch):
    source = image_factory()
    target = source.with_suffix(".webp")
    original = fs.publish_new

    def raced(staging, destination):
        destination.write_bytes(b"FOREIGN_OUTPUT_SENTINEL")
        return original(staging, destination)

    monkeypatch.setattr(fs, "publish_new", raced)
    result = convert(ConversionRequest([source]))
    assert result.status == "failed" and result.items[0].error.code == "OUTPUT_EXISTS"
    assert target.read_bytes() == b"FOREIGN_OUTPUT_SENTINEL"
    assert not list(source.parent.glob(".ic-*"))


@pytest.mark.parametrize("kind", ["source", "parent"])
def test_changed_source_or_parent_fails_closed(image_factory, tmp_path, monkeypatch, kind):
    source = image_factory()
    output = tmp_path / "out"
    output.mkdir()
    original = imaging.encode
    replacement = b"CHANGED_SOURCE_SENTINEL"

    def changed(*args, **kwargs):
        prepared = original(*args, **kwargs)
        if kind == "source":
            source.write_bytes(replacement)
        else:
            output.rename(tmp_path / "moved")
            output.mkdir()
            (output / "foreign").write_bytes(b"FOREIGN_DIRECTORY_SENTINEL")
        return prepared

    monkeypatch.setattr(imaging, "encode", changed)
    result = convert(ConversionRequest([source], output_directory=output))
    assert result.items[0].error.code == (
        "SOURCE_CHANGED" if kind == "source" else "DESTINATION_CHANGED"
    )
    assert result.counts.published == 0
    assert not (output / "source.webp").exists()
    if kind == "source":
        assert source.read_bytes() == replacement
        assert not list(output.glob(".ic-*"))
    else:
        assert (output / "foreign").read_bytes() == b"FOREIGN_DIRECTORY_SENTINEL"
        assert result.items[0].warnings[0].code == "TEMP_CLEANUP_FAILED"


@pytest.mark.parametrize(
    "boundary", ["save", "verify", "unsupported", "denied", "readback", "cleanup"]
)
def test_fault_boundaries_real_pipeline(image_factory, monkeypatch, boundary):
    source = image_factory()
    before = source.read_bytes()
    get_capabilities()  # Fault injection is after the real capability probe.
    if boundary == "save":

        def broken_save(self, fp, *args, **kwargs):
            Path(fp).write_bytes(b"PARTIAL_STAGING_SENTINEL")
            raise OSError("PRIVATE_EXCEPTION_SENTINEL")

        monkeypatch.setattr(Image.Image, "save", broken_save)
    elif boundary in ("verify", "readback"):
        original = imaging.verify_image
        calls = 0

        def broken_verify(*args):
            nonlocal calls
            calls += 1
            if boundary == "verify" or calls == 2:
                raise fs.fail(imaging.ErrorCode.VERIFICATION_FAILED, "verification")
            return original(*args)

        monkeypatch.setattr(imaging, "verify_image", broken_verify)
    elif boundary in ("unsupported", "denied"):

        def broken_link(*args):
            if boundary == "denied":
                raise PermissionError(errno.EACCES, "PRIVATE_EXCEPTION_SENTINEL")
            raise OSError(errno.ENOTSUP, "PRIVATE_EXCEPTION_SENTINEL")

        monkeypatch.setattr(os, "link", broken_link)
    else:
        original = fs.Staging.cleanup

        def occupied(staging):
            (staging.directory / "foreign").write_bytes(b"FOREIGN_TEMP_SENTINEL")
            return original(staging)

        monkeypatch.setattr(fs.Staging, "cleanup", occupied)
    result = convert(ConversionRequest([source]))
    (item,) = result.items
    assert source.read_bytes() == before
    codes = {
        "save": "ENCODE_FAILED",
        "verify": "VERIFICATION_FAILED",
        "unsupported": "PUBLICATION_UNSUPPORTED",
        "denied": "OUTPUT_ACCESS_DENIED",
        "readback": "PUBLISHED_UNVERIFIED",
    }
    if boundary in codes:
        assert item.error.code == codes[boundary], result
    if boundary == "readback":
        assert result.status == "partial" and result.counts.published == 1
        assert item.artifact.publication == "unverified" and item.status == "failed"
        with assert_image(item.destination):
            pass
    elif boundary == "cleanup":
        assert result.status == "partial" and item.status == "succeeded"
        assert item.warnings[0].code == "TEMP_CLEANUP_FAILED"
        (remaining,) = source.parent.glob(".ic-*")
        assert (remaining / "foreign").read_bytes() == b"FOREIGN_TEMP_SENTINEL"
        assert not (remaining / "payload").exists()
    else:
        assert result.counts.published == 0 and not source.with_suffix(".webp").exists()
    if boundary != "cleanup":
        assert not list(source.parent.glob(".ic-*"))


def test_replaced_staging_not_removed(image_factory, monkeypatch):
    source = image_factory()
    original = fs.Staging.cleanup

    def replaced(staging):
        old = staging.file.with_name("our-moved-payload")
        staging.file.rename(old)
        staging.file.write_bytes(b"FOREIGN_STAGING_SENTINEL")
        return original(staging)

    monkeypatch.setattr(fs.Staging, "cleanup", replaced)
    result = convert(ConversionRequest([source]))
    assert result.status == "partial"
    (directory,) = source.parent.glob(".ic-*")
    assert (directory / "payload").read_bytes() == b"FOREIGN_STAGING_SENTINEL"
    assert (directory / "our-moved-payload").exists()


@pytest.mark.parametrize("failure", ["open", "after_open"])
def test_partial_staging_setup_is_owned_and_cleaned(image_factory, monkeypatch, failure):
    source = image_factory()
    if failure == "open":
        original = Path.open

        def denied(path, *args, **kwargs):
            if path.name == "payload":
                raise PermissionError("PRIVATE_SETUP_SENTINEL")
            return original(path, *args, **kwargs)

        monkeypatch.setattr(Path, "open", denied)
    else:
        original = fs.Staging.initialize

        def incomplete(staging):
            original(staging)
            raise OSError("PRIVATE_SETUP_SENTINEL")

        monkeypatch.setattr(fs.Staging, "initialize", incomplete)
    result = convert(ConversionRequest([source]))
    assert result.status == "failed" and result.counts.published == 0
    assert result.items[0].error.code == (
        "OUTPUT_ACCESS_DENIED" if failure == "open" else "WRITE_FAILED"
    )
    assert not list(source.parent.glob(".ic-*"))
    assert not source.with_suffix(".webp").exists()


def test_artifact_digest_is_final_bytes(image_factory):
    result = convert(ConversionRequest([image_factory()]))
    artifact = result.items[0].artifact
    assert artifact.sha256 == hashlib.sha256(artifact.path.read_bytes()).hexdigest()
    assert artifact.size_bytes == artifact.path.stat().st_size


def test_two_process_no_clobber(image_factory, tmp_path):
    source = image_factory()
    before = source.read_bytes()
    processes = []
    harness = Path(__file__).with_name("race_harness.py")
    repo = Path(__file__).resolve().parents[1]
    try:
        for index in range(2):
            processes.append(
                subprocess.Popen(
                    [sys.executable, str(harness), str(source), str(tmp_path), str(index)],
                    cwd=repo,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            )
        deadline = time.monotonic() + 25
        while not all((tmp_path / f"ready-{i}").exists() for i in range(2)):
            assert time.monotonic() < deadline, "publish barrier not reached"
            assert all(p.poll() is None for p in processes)
            time.sleep(0.02)
        (tmp_path / "go").touch()
        reports = []
        for process in processes:
            stdout, stderr = process.communicate(timeout=30)
            assert process.returncode == 0, stderr.decode("utf-8")
            reports.append(json.loads(stdout))
        assert sorted(report["status"] for report in reports) == ["failed", "succeeded"]
        assert [r["code"] for r in reports if r["status"] == "failed"] == ["OUTPUT_EXISTS"]
        with assert_image(source.with_suffix(".webp")):
            pass
        assert source.read_bytes() == before
    finally:
        for process in processes:
            if process.poll() is None:
                process.kill()
            process.communicate(timeout=10)
