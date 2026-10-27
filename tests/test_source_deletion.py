"""Opt-in deletion through the real public owner, only newly owned synthetic images."""

import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import pytest
from PIL import Image

from image_compressor import (
    CancellationToken,
    ConversionRequest,
    convert,
    diagnostics,
    discovery,
    imaging,
)
from image_compressor import _windows_deletion as native
from image_compressor import filesystem as fs
from image_compressor.models import ErrorCode
from image_compressor.serialization import to_json

from .image_fixtures import alpha_extrema, write_alpha_png, write_sample_png


@pytest.mark.parametrize("fmt", ["WEBP", "JPEG"])
@pytest.mark.parametrize("delete", [False, True])
def test_native_public_conversion_and_default_false_control(image_factory, tmp_path, fmt, delete):
    assert os.name == "nt", "This required native positive is qualified on Windows, never skipped."
    source = image_factory("Вход қаз/原本 image.png")
    before = source.read_bytes()
    parent = tmp_path / "Résultat жаңа"
    parent.mkdir()
    output = parent / ("新 output.webp" if fmt == "WEBP" else "新 output.jpg")
    result = convert(
        ConversionRequest([source], output_format=fmt, output_path=output, delete_original=delete)
    )
    assert result.status == "succeeded", result
    assert result.options.delete_original is delete
    assert result.counts.succeeded == result.counts.published == 1
    assert result.counts.deleted == int(delete)
    (item,) = result.items
    assert item.status == "succeeded" and item.error is None and not item.warnings
    assert item.source_disposition == ("deleted" if delete else "retained")
    assert item.artifact.publication == "verified"
    assert item.artifact.size_bytes == output.stat().st_size
    assert item.artifact.sha256 == hashlib.sha256(output.read_bytes()).hexdigest()
    with Image.open(output) as image:
        image.load()
        assert image.format == fmt and image.size == (80, 60)
        r, g, b = image.convert("RGB").getpixel((20, 20))
        assert b > g > r
    if delete:
        assert not source.exists()
    else:
        assert source.read_bytes() == before
    payload = to_json(result)
    assert payload["options"]["delete_original"] is delete
    assert payload["counts"]["deleted"] == int(delete)
    assert payload["items"][0]["source_disposition"] == item.source_disposition
    assert not list(parent.glob(".ic-*"))
    moved = tmp_path / "released result parent"
    parent.rename(moved)  # No lingering guard may prevent the next independent operation.
    source.parent.rename(tmp_path / "released source parent")


def test_unavailable_support_rejects_before_discovery_false_remains_useful(
    image_factory, monkeypatch,
):
    source = image_factory()
    before = source.read_bytes()
    monkeypatch.setattr(native, "available", lambda: False)
    with monkeypatch.context() as patch:
        patch.setattr(discovery, "build_manifest", lambda *a, **k: pytest.fail("discovery reached"))
        result = convert(ConversionRequest([source], delete_original=True))
    assert result.status == "rejected" and result.errors[0].code == "DESTRUCTIVE_MODE_UNSUPPORTED"
    assert not result.items and result.counts.deleted == result.counts.published == 0
    assert source.read_bytes() == before
    monkeypatch.setattr(native, "_api", lambda: pytest.fail("False must not initialize native API"))
    control = convert(ConversionRequest([source]))
    assert control.status == "succeeded" and control.counts.deleted == 0
    assert source.read_bytes() == before


@pytest.mark.parametrize("value", [0, 1, "true", None])
def test_explicit_delete_is_strict_bool_before_effects(image_factory, value):
    source = image_factory()
    before = source.read_bytes()
    result = convert(ConversionRequest([source], delete_original=value))
    assert result.status == "rejected" and result.errors[0].code == "INVALID_REQUEST"
    assert result.errors[0].field == "delete_original" and result.counts.published == 0
    assert source.read_bytes() == before and not source.with_suffix(".webp").exists()


@pytest.mark.parametrize("path", [r"\\server.invalid\share\private.png",
                                  r"C:\private.png:stream", r"\\?\C:\private.png",
                                  r"\\.\C:\private.png", r"C:\NUL.png"])
def test_unsafe_namespace_rejected_without_traversal(path, monkeypatch):
    original = discovery.build_manifest

    def no_unsafe_inputs(inputs, **kwargs):
        assert inputs == ()  # No UNC/device/ADS lookup, even for negative tests.
        return original(inputs, **kwargs)

    monkeypatch.setattr(discovery, "build_manifest", no_unsafe_inputs)
    result = convert(ConversionRequest([path], delete_original=True))
    assert result.status == "failed" and result.items[0].error.code == "UNSAFE_PATH", result
    assert result.counts.published == result.counts.deleted == 0


@pytest.mark.parametrize("ancestor", [False, True])
def test_real_reparse_source_refused_without_following(image_factory, tmp_path, ancestor):
    source = image_factory("real/source.png")
    before = source.read_bytes()
    link = tmp_path / ("linked-parent" if ancestor else "link.png")
    os.symlink(source.parent if ancestor else source, link, target_is_directory=ancestor)
    selected = link / source.name if ancestor else link
    result = convert(ConversionRequest([selected], delete_original=True))
    assert result.items[0].error.code == "UNSAFE_PATH", result
    assert result.counts.deleted == result.counts.published == 0
    assert source.read_bytes() == before and link.is_symlink()


@pytest.mark.parametrize("edge", ["snapshot", "digest", "volume", "before_acquire_content"])
def test_source_checks_and_unsupported_volume_fail_closed(image_factory, monkeypatch, edge):
    source = image_factory()
    before = source.read_bytes()
    if edge == "snapshot":
        original = native.DeletionGuard.check_source

        def changed(guard):
            original(guard)
            raise fs.fail(ErrorCode.SOURCE_CHANGED, "source_deletion")

        monkeypatch.setattr(native.DeletionGuard, "check_source", changed)
    elif edge == "digest":
        original = fs.digest_stream
        calls = []

        def different(stream):
            value = original(stream)
            calls.append(value)
            return (value[0], "0" * 64) if len(calls) == 4 else value

        monkeypatch.setattr(fs, "digest_stream", different)
    elif edge == "volume":
        def unsupported(handle):
            raise fs.fail(ErrorCode.DESTRUCTIVE_MODE_UNSUPPORTED, "source_deletion")

        # Native volume-query edge, not a claim of an actual FAT/removable-volume test.
        monkeypatch.setattr(native._Handle, "require_ntfs", unsupported)
    else:
        original = native.DeletionGuard.acquire

        def changed(cls, path, *args):
            with source.open("ab") as stream:
                stream.write(b"OWNED_CHANGED_CONTENT")
            return original(path, *args)

        monkeypatch.setattr(native.DeletionGuard, "acquire", classmethod(changed))
    result = convert(ConversionRequest([source], delete_original=True))
    item = result.items[0]
    assert item.source_disposition == "retained" and result.counts.deleted == 0
    if edge in ("snapshot", "digest"):
        assert result.status == "partial" and item.status == "succeeded"
        assert item.artifact.publication == "verified" and item.warnings[0].code == "SOURCE_CHANGED"
        if edge == "digest":
            assert len(calls) == 4
    else:
        assert item.status == "failed" and item.artifact is None
        assert result.counts.published == 0
        expected = "DESTRUCTIVE_MODE_UNSUPPORTED" if edge == "volume" else "SOURCE_CHANGED"
        assert item.error.code == expected
    suffix = b"OWNED_CHANGED_CONTENT" if edge == "before_acquire_content" else b""
    assert source.read_bytes() == before + suffix
    source.rename(source.with_name("released.png"))


@pytest.mark.parametrize("boundary", ["encode", "staging_verify", "link"])
def test_true_failure_before_publication_never_disposes(image_factory, monkeypatch, boundary):
    source = image_factory()
    before = source.read_bytes()
    imaging.get_capabilities()
    if boundary == "encode":
        def failed_save(*args, **kwargs):
            raise OSError("PRIVATE_SAVE_SENTINEL")

        monkeypatch.setattr(imaging.Image.Image, "save", failed_save)
    elif boundary == "staging_verify":
        monkeypatch.setattr(imaging, "verify_image", lambda *a: (_ for _ in ()).throw(
            fs.fail(ErrorCode.VERIFICATION_FAILED, "verification")))
    else:
        monkeypatch.setattr(os, "link", lambda *a: (_ for _ in ()).throw(
            OSError("PRIVATE_LINK_SENTINEL")))
    monkeypatch.setattr(native.DeletionGuard, "accept_disposition",
                        lambda *a: pytest.fail("Disposition reached before verified publication"))
    result = convert(ConversionRequest([source], delete_original=True))
    assert result.status == "failed" and result.counts.published == result.counts.deleted == 0
    assert result.items[0].error.code == {
        "encode": "ENCODE_FAILED", "staging_verify": "VERIFICATION_FAILED",
        "link": "PUBLICATION_FAILED",
    }[boundary]
    assert source.read_bytes() == before and not list(source.parent.glob(".ic-*"))


def test_true_conflicts_late_foreign_partial_and_repeat(image_factory, tmp_path, monkeypatch):
    a, b = image_factory("same.png"), image_factory("same.jpg")
    before = {p: p.read_bytes() for p in (a, b)}
    conflict = convert(ConversionRequest([a, b], delete_original=True))
    assert [i.error.code for i in conflict.items] == ["TARGET_CONFLICT", "TARGET_CONFLICT"]
    same = image_factory("same-format.webp")
    same_result = convert(ConversionRequest([same], postfix="", delete_original=True))
    assert same_result.items[0].error.code == "INPUT_OUTPUT_CONFLICT"
    late = image_factory("late.png")
    publish = fs.publish_new
    with monkeypatch.context() as patch:
        def foreign(staging, destination):
            destination.write_bytes(b"FOREIGN_DESTINATION_SENTINEL")
            publish(staging, destination)

        patch.setattr(fs, "publish_new", foreign)
        result = convert(ConversionRequest([late], delete_original=True))
    assert result.items[0].error.code == "OUTPUT_EXISTS" and result.counts.deleted == 0
    assert late.with_suffix(".webp").read_bytes() == b"FOREIGN_DESTINATION_SENTINEL"
    good, retained = image_factory("good.png"), image_factory("retained.png")
    bad = tmp_path / "bad.png"
    bad.write_bytes(b"OWNED_CORRUPT_IMAGE")
    flush = native.DeletionGuard.flush_final
    with monkeypatch.context() as patch:
        def refused(guard):
            if guard.path == retained:
                raise fs.fail(ErrorCode.SOURCE_DELETION_FAILED, "source_deletion")
            flush(guard)

        patch.setattr(native.DeletionGuard, "flush_final", refused)
        result = convert(ConversionRequest([good, bad, retained], delete_original=True))
    assert result.status == "partial" and result.counts.deleted == 1
    assert result.counts.succeeded == result.counts.published == 2 and result.counts.failed == 1
    assert [i.source_disposition for i in result.items] == ["deleted", "retained", "retained"]
    assert not good.exists() and retained.exists() and bad.read_bytes() == b"OWNED_CORRUPT_IMAGE"
    again = convert(ConversionRequest([retained], delete_original=True))
    assert again.items[0].error.code == "OUTPUT_EXISTS" and retained.exists()
    assert again.counts.deleted == 0 and all(p.read_bytes() == data for p, data in before.items())


@pytest.mark.parametrize("admitted", [False, True])
def test_true_single_late_cancel_is_not_undo(image_factory, monkeypatch, admitted):
    source = image_factory()
    token = CancellationToken()
    owner, name = (
        (native.DeletionGuard, "accept_disposition") if admitted else (fs, "publish_new")
    )
    original = getattr(owner, name)

    def cancel(*args):
        token.cancel()
        return original(*args)

    monkeypatch.setattr(owner, name, cancel)
    result = convert(ConversionRequest([source], delete_original=True), cancellation=token)
    assert result.status == ("succeeded" if admitted else "cancelled")
    assert result.counts.succeeded == result.counts.published == 1 and result.counts.cancelled == 0
    assert result.counts.deleted == int(admitted) and source.exists() is (not admitted)
    assert result.items[0].artifact.publication == "verified"


def test_actual_native_headless_with_forbidden_ui_and_terminal(image_factory):
    source = image_factory()
    script = r'''
import builtins, importlib.abc, json, sys
sys.path.insert(0, sys.argv[1])
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('PyQt6','PySide6','gui','gui_pyside6_v2','argparse'):
            raise AssertionError('Forbidden dependency')
sys.meta_path.insert(0, Block())
def forbidden(*args, **kwargs):
    raise AssertionError('Forbidden terminal call')
builtins.input = builtins.print = forbidden
from image_compressor import ConversionRequest, convert
from image_compressor.serialization import to_json
result = convert(ConversionRequest([sys.argv[2]],delete_original=True))
assert result.status == 'succeeded' and result.counts.deleted == 1
sys.stdout.write(json.dumps(to_json(result)))
'''
    process = subprocess.run([sys.executable, "-I", "-B", "-c", script,
                              str(Path(__file__).resolve().parents[1]), str(source)],
                             cwd=source.parent, capture_output=True, timeout=30)
    assert process.returncode == 0 and not process.stderr
    payload = json.loads(process.stdout)
    assert payload["counts"]["deleted"] == 1 and not source.exists()
    assert payload["items"][0]["source_disposition"] == "deleted"


def test_native_file_handler_reason_disposition_counts_and_privacy(
    image_factory, tmp_path, monkeypatch,
):
    source = image_factory("PRIVATE_PATH/PRIVATE_SOURCE.png")
    retained = image_factory("PRIVATE_PATH/PRIVATE_RETAINED.png")
    digests = [hashlib.sha256(p.read_bytes()).hexdigest().encode() for p in (source, retained)]
    path = tmp_path / "safe-native.log"
    handler = logging.FileHandler(path, encoding="utf-8")
    logger = diagnostics.LOGGER
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    flush = native.DeletionGuard.flush_final

    def refused(guard):
        if guard.path == retained:
            raise fs.fail(ErrorCode.SOURCE_DELETION_FAILED, "source_deletion")
        flush(guard)

    monkeypatch.setattr(native.DeletionGuard, "flush_final", refused)
    try:
        result = convert(ConversionRequest([source, retained], delete_original=True,
                                           postfix="PRIVATE_POSTFIX"))
        handler.flush()
        data = path.read_bytes()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
        handler.close()
    assert result.status == "partial" and result.counts.deleted == 1
    assert b"source_disposition=deleted" in data and b"source_disposition=retained" in data
    assert b"deleted=1" in data and b"reason=SOURCE_DELETION_FAILED" in data
    assert b"event=conversion_finished" in data and b"PRIVATE_" not in data
    assert all(digest not in data for digest in digests)


def test_directory_manifest_duplicates_and_only_regular_files_deleted(image_factory, tmp_path):
    sources = [image_factory("input/one.png"), image_factory("input/sub/two.png")]
    output = sources[0].parent / "output"
    output.mkdir()
    result = convert(ConversionRequest([sources[0].parent, sources[0]], recursive=True,
                                       output_directory=output, delete_original=True))
    assert result.status == "succeeded" and result.counts.deleted == 2
    assert result.counts.duplicates == 1 and result.counts.succeeded == result.counts.published == 2
    assert all(not p.exists() for p in sources)
    assert all(p.parent.is_dir() for p in sources) and output.is_dir()
    for item in result.items:
        with Image.open(item.destination) as image:
            image.load()
            assert image.format == "WEBP" and image.size == (80, 60)


def test_real_junction_ancestor_is_refused(image_factory, tmp_path):
    source = image_factory("owned-target/source.png")
    before = source.read_bytes()
    junction = tmp_path / "owned-junction"
    # Creation only, no shell deletion/privilege/ACL fallback. All paths freshly owned.
    process = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(junction),
                              str(source.parent)], cwd=tmp_path, capture_output=True, timeout=15)
    assert process.returncode == 0, process.stderr
    result = convert(ConversionRequest([junction / source.name], delete_original=True))
    assert result.items[0].error.code == "UNSAFE_PATH" and result.counts.deleted == 0
    assert source.read_bytes() == before and not source.with_suffix(".webp").exists()


def test_true_observer_formatter_failures_do_not_retry_or_leak(image_factory, tmp_path, capsys):
    source = image_factory()
    path = tmp_path / "broken.log"

    class BrokenFormatter(logging.Formatter):
        def format(self, record):
            raise RuntimeError("PRIVATE_FORMATTER_SENTINEL")

    handler = logging.FileHandler(path, encoding="utf-8")
    handler.setFormatter(BrokenFormatter())
    logger = diagnostics.LOGGER
    old_level = logger.level
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    calls = []

    def observer(event):
        calls.append(event.phase)
        raise ValueError("PRIVATE_OBSERVER_SENTINEL")

    try:
        result = convert(ConversionRequest([source], delete_original=True), on_progress=observer)
        handler.flush()
    finally:
        logger.removeHandler(handler)
        logger.setLevel(old_level)
        handler.close()
    assert result.status == "succeeded" and result.counts.deleted == 1 and not source.exists()
    assert len(calls) == 1 and result.warnings[0].code == "OBSERVER_FAILED"
    assert len(list(source.parent.glob("*.webp"))) == 1
    assert path.read_bytes() == b"" and "PRIVATE_" not in capsys.readouterr().err


@pytest.mark.parametrize("alpha", [255, 73])
def test_locked_source_alpha_policy_is_preserved_with_real_deletion(tmp_path, alpha):
    source = write_alpha_png(tmp_path / "alpha.png", "rgba", alpha=alpha)
    result = convert(ConversionRequest([source], delete_original=True))
    assert result.status == "succeeded" and result.counts.deleted == 1 and not source.exists()
    with Image.open(result.items[0].destination) as image:
        image.load()
        assert alpha_extrema(image) == (alpha, alpha)


@pytest.mark.parametrize("depth", [8, 16])
@pytest.mark.parametrize("color_type", [2, 6])
def test_locked_source_png_precision_refusal_remains_strict(tmp_path, depth, color_type):
    source = write_sample_png(tmp_path / "precision.png", depth=depth, color_type=color_type)
    before = source.read_bytes()
    result = convert(ConversionRequest([source], delete_original=True))
    if depth == 16:
        assert result.items[0].error.code == "IMAGE_MODE_UNSUPPORTED"
        assert result.counts.deleted == result.counts.published == 0
        assert source.read_bytes() == before
    else:
        assert result.status == "succeeded" and result.counts.deleted == 1 and not source.exists()
        with Image.open(result.items[0].destination) as image:
            image.load()
            assert alpha_extrema(image) == ((128, 128) if color_type == 6 else (255, 255))


@pytest.mark.parametrize("junction", [False, True])
def test_true_rejects_lexical_output_dot_chain_before_normalization(
    image_factory, tmp_path, junction,
):
    source = image_factory()
    before = source.read_bytes()
    parent = tmp_path / "destination-parent"
    if junction:
        target = tmp_path / "owned-junction-target"
        target.mkdir()
        process = subprocess.run(["cmd.exe", "/d", "/c", "mklink", "/J", str(parent), str(target)],
                                 cwd=tmp_path, capture_output=True, timeout=15)
        assert process.returncode == 0
    else:
        parent.mkdir()
    # Collapsing '..' first would hide a reparse ancestor and admit the wrong request.
    destination = parent / ".." / "result.webp"
    result = convert(ConversionRequest([source], output_path=destination, delete_original=True))
    assert result.status == "failed" and result.items[0].error.code == "UNSAFE_PATH", result
    assert result.counts.published == result.counts.deleted == 0
    assert result.items[0].artifact is None and result.items[0].source_disposition == "retained"
    assert source.read_bytes() == before and not (tmp_path / "result.webp").exists()
