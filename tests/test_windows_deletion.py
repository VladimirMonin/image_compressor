"""Real Windows sharing/identity schedules; mocks only isolate specified native faults."""

import ctypes
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from image_compressor import CancellationToken, ConversionRequest, convert, imaging
from image_compressor import _windows_deletion as native
from image_compressor import filesystem as fs
from image_compressor.models import ErrorCode

from .conftest import assert_image


def requested(sources, **kwargs):
    return ConversionRequest(sources, delete_original=True, **kwargs)


def mutations(source, destination, phase, tmp_path):
    child = subprocess.run(
        [sys.executable, "-I", "-B", str(Path(__file__).with_name("deletion_race_harness.py")),
         str(source), str(destination), phase],
        cwd=tmp_path, capture_output=True, timeout=30,
    )
    (tmp_path / f"{phase}-child.stdout").write_bytes(child.stdout)
    (tmp_path / f"{phase}-child.stderr").write_bytes(child.stderr)
    assert child.returncode == 0 and not child.stderr
    reports = json.loads(child.stdout)
    assert len(reports) == (4 if phase == "source" else 2)
    assert all(report["refused"] and report["winerror"] in (5, 32) for report in reports), reports


def test_real_child_source_and_both_parent_guards_and_final_guard(
    image_factory, tmp_path, monkeypatch,
):
    source = image_factory("input/source.png")
    output = tmp_path / "output"
    output.mkdir()
    destination = output / "source.webp"
    encode, verify = imaging.encode, imaging.verify_image
    events = []

    def guarded_encode(*args, **kwargs):
        mutations(source, destination, "source", tmp_path)
        events.append("source_guard")
        return encode(*args, **kwargs)

    def guarded_verify(path, *args):
        result = verify(path, *args)
        if not isinstance(path, Path):
            mutations(source, destination, "final", tmp_path)
            events.append("final_verified")
        return result

    flush = native.DeletionGuard.flush_final
    accept = native.DeletionGuard.accept_disposition

    def flushed(guard):
        flush(guard)
        events.append("flushed")

    def accepted(guard):
        assert events == ["source_guard", "final_verified", "flushed"]
        assert not list(output.glob(".ic-*"))
        events.append("disposition")
        accept(guard)

    monkeypatch.setattr(imaging, "encode", guarded_encode)
    monkeypatch.setattr(imaging, "verify_image", guarded_verify)
    monkeypatch.setattr(native.DeletionGuard, "flush_final", flushed)
    monkeypatch.setattr(native.DeletionGuard, "accept_disposition", accepted)
    result = convert(requested([source], output_directory=output))
    assert result.status == "succeeded", result
    assert result.counts.deleted == 1 and not source.exists()
    assert events[-1] == "disposition"
    with assert_image(destination):
        pass
    source.parent.rename(tmp_path / "released-input")
    output.rename(tmp_path / "released-output")


def test_preacquire_replacement_is_not_rebound_or_deleted(image_factory, tmp_path, monkeypatch):
    source = image_factory("source.png")
    replacement = image_factory("replacement.png", color=(210, 32, 120))
    before, other = source.read_bytes(), replacement.read_bytes()
    moved = tmp_path / "moved-original.png"
    acquire = native.DeletionGuard.acquire

    def replaced(cls, path, *args):
        source.rename(moved)
        replacement.rename(source)
        return acquire(path, *args)

    monkeypatch.setattr(native.DeletionGuard, "acquire", classmethod(replaced))
    result = convert(requested([source]))
    assert result.items[0].error.code == "SOURCE_CHANGED", result
    assert result.counts.published == result.counts.deleted == 0
    assert source.read_bytes() == other and moved.read_bytes() == before
    assert not source.with_suffix(".webp").exists() and not list(tmp_path.glob(".ic-*"))
    source.rename(tmp_path / "released-replacement.png")


@pytest.mark.parametrize("kind", ["replaced", "busy", "verify"])
def test_final_before_guard_fault_preserves_source_and_foreign(
    image_factory, tmp_path, monkeypatch, kind,
):
    source = image_factory()
    before = source.read_bytes()
    published = fs.publish_new
    held = []
    moved = tmp_path / "published-moved.webp"

    def changed(staging, destination):
        published(staging, destination)
        if kind == "replaced":
            destination.rename(moved)
            destination.write_bytes(b"FOREIGN_FINAL_SENTINEL")
        elif kind == "busy":
            held.append(destination.open("r+b"))

    verify = imaging.verify_image

    def failed_verify(path, *args):
        if not isinstance(path, Path):
            raise fs.fail(ErrorCode.VERIFICATION_FAILED, "readback")
        return verify(path, *args)

    monkeypatch.setattr(fs, "publish_new", changed)
    if kind == "verify":
        monkeypatch.setattr(imaging, "verify_image", failed_verify)
    try:
        result = convert(requested([source]))
        assert result.status == "partial" and result.counts.published == 1, result
        assert result.counts.succeeded == result.counts.deleted == 0
        assert result.items[0].error.code == "PUBLISHED_UNVERIFIED"
        assert result.items[0].artifact.publication == "unverified"
        assert result.items[0].source_disposition == "retained"
        assert source.read_bytes() == before
        if kind == "replaced":
            assert source.with_suffix(".webp").read_bytes() == b"FOREIGN_FINAL_SENTINEL"
            with assert_image(moved):
                pass
        assert not list(tmp_path.glob(".ic-*"))
    finally:
        for stream in held:
            stream.close()
    source.rename(tmp_path / "released.png")


@pytest.mark.parametrize("edge", ["FlushFileBuffers", "SetFileInformationByHandle"])
def test_native_false_after_real_verified_output(image_factory, monkeypatch, edge):
    source = image_factory()
    before = source.read_bytes()
    calls = []

    def refused(*args):
        calls.append(1)
        return 0

    monkeypatch.setattr(native._api().dll, edge, refused)
    result = convert(requested([source]))
    assert result.status == "partial" and calls == [1], result
    assert result.counts.succeeded == result.counts.published == 1
    assert result.counts.deleted == 0
    item = result.items[0]
    assert item.status == "succeeded" and item.error is None
    assert item.source_disposition == "retained"
    assert [w.code for w in item.warnings] == ["SOURCE_DELETION_FAILED"]
    assert source.read_bytes() == before
    with assert_image(item.destination):
        pass


@pytest.mark.parametrize("kind", ["foreign_file", "foreign_child"])
def test_staging_cleanup_is_once_owned_and_skips_deletion(
    image_factory, tmp_path, monkeypatch, kind,
):
    source = image_factory()
    before = source.read_bytes()
    cleanup = fs.Staging.cleanup
    calls = []

    def occupied(staging):
        calls.append(staging.directory)
        if kind == "foreign_file":
            staging.file.rename(staging.file.with_name("our-moved-payload"))
            staging.file.write_bytes(b"FOREIGN_STAGING_SENTINEL")
        else:
            (staging.directory / "foreign").write_bytes(b"FOREIGN_CHILD_SENTINEL")
        return cleanup(staging)

    monkeypatch.setattr(fs.Staging, "cleanup", occupied)
    result = convert(requested([source]))
    assert result.status == "partial" and len(calls) == 1, result
    item = result.items[0]
    assert item.status == "succeeded" and item.artifact.publication == "verified"
    assert item.source_disposition == "retained" and result.counts.deleted == 0
    assert [w.code for w in item.warnings] == ["TEMP_CLEANUP_FAILED", "SOURCE_DELETION_SKIPPED"]
    assert source.read_bytes() == before
    directory = calls[0]
    if kind == "foreign_file":
        assert (directory / "payload").read_bytes() == b"FOREIGN_STAGING_SENTINEL"
        assert (directory / "our-moved-payload").exists()
    else:
        assert (directory / "foreign").read_bytes() == b"FOREIGN_CHILD_SENTINEL"
        assert not (directory / "payload").exists()
    with assert_image(item.destination):
        pass


def test_accepted_real_disposition_ambiguous_confirmation_is_unknown_not_retry(
    image_factory, monkeypatch,
):
    source = image_factory()
    accepted = native.DeletionGuard.accept_disposition
    calls = []

    def once(guard):
        calls.append(1)
        accepted(guard)

    monkeypatch.setattr(native.DeletionGuard, "accept_disposition", once)
    monkeypatch.setattr(native, "_confirm_deleted", lambda *args: False)
    result = convert(requested([source]))
    assert result.status == "partial" and calls == [1]
    # Real effect, injected readback only.
    assert result.counts.deleted == 0 and not source.exists()
    item = result.items[0]
    assert item.status == "succeeded" and item.source_disposition == "unknown"
    assert [w.code for w in item.warnings] == ["SOURCE_DELETION_UNCONFIRMED"]
    with assert_image(item.destination):
        pass


def test_real_compatible_metadata_handle_pending_witness(image_factory, tmp_path):
    source = image_factory()
    metadata = native._Handle.open(source, native._ATTRIBUTES, 7)
    try:
        result = convert(requested([source]))
        pending = metadata.snapshot().pending
        observed = {"status": result.status, "pending": pending,
                    "disposition": result.items[0].source_disposition,
                    "deleted": result.counts.deleted}
        witness = tmp_path / "native-pending-witness.json"
        witness.write_text(json.dumps(observed), encoding="utf-8")
        assert pending, observed
        assert result.status == "partial", observed
        assert result.items[0].source_disposition == "unknown", observed
        assert result.counts.deleted == 0
    finally:
        metadata.close()
    assert not source.exists()
    with assert_image(source.with_suffix(".webp")):
        pass


@pytest.mark.parametrize("kind", ["readonly", "busy", "hardlink"])
def test_preacquire_refusals_have_no_staging_and_false_control(
    image_factory, tmp_path, kind,
):
    source = image_factory()
    before = source.read_bytes()
    stream = None
    if kind == "readonly":
        source.chmod(stat.S_IREAD)
    elif kind == "busy":
        stream = source.open("rb")
    else:
        os.link(source, tmp_path / "alias.png")
    try:
        result = convert(requested([source]))
        assert result.status == "failed" and result.counts.published == result.counts.deleted == 0
        assert result.items[0].error.code == (
            "DESTRUCTIVE_MODE_UNSUPPORTED" if kind == "hardlink" else "SOURCE_DELETION_FAILED"
        ), result
        assert result.items[0].source_disposition == "retained"
        assert source.read_bytes() == before and not list(tmp_path.glob(".ic-*"))
        preserved = convert(ConversionRequest([source]))
        assert preserved.status == "succeeded" and preserved.counts.deleted == 0
        assert source.read_bytes() == before
        with assert_image(preserved.items[0].destination):
            pass
    finally:
        if stream:
            stream.close()
        if kind == "readonly":
            source.chmod(stat.S_IREAD | stat.S_IWRITE)


@pytest.mark.parametrize("phase", ["encode", "published", "flushed", "admitted"])
def test_cancel_checkpoints_preserve_effects(image_factory, monkeypatch, phase):
    sources = [image_factory("first.png"), image_factory("second.png")]
    snapshots = [p.read_bytes() for p in sources]
    token = CancellationToken()
    owner, name = {
        "encode": (imaging, "encode"), "published": (fs, "publish_new"),
        "flushed": (native.DeletionGuard, "flush_final"),
        "admitted": (native.DeletionGuard, "accept_disposition"),
    }[phase]
    original = getattr(owner, name)

    def cancel(*args, **kwargs):
        if phase == "admitted":
            token.cancel()  # Checkpoint already passed; cancellation is not Undo.
        value = original(*args, **kwargs)
        if phase != "admitted":
            token.cancel()
        return value

    monkeypatch.setattr(owner, name, cancel)
    result = convert(requested(sources), cancellation=token)
    assert result.status == "cancelled", result
    assert result.items[1].status == "cancelled" and sources[1].read_bytes() == snapshots[1]
    assert result.counts.deleted == int(phase == "admitted")
    first = result.items[0]
    if phase == "encode":
        assert first.status == "cancelled" and result.counts.published == 0
    else:
        assert first.status == "succeeded" and first.artifact.publication == "verified"
        with assert_image(first.destination):
            pass
        if phase != "admitted":
            assert first.warnings[0].code == "CANCELLED"
            assert first.warnings[0].stage == "source_deletion"
    if phase == "admitted":
        assert not sources[0].exists() and first.source_disposition == "deleted"
    else:
        assert sources[0].read_bytes() == snapshots[0] and first.source_disposition == "retained"


@pytest.mark.parametrize("phase", ["flush", "source_close", "all_close"])
def test_unexpected_lifetime_failure_preserves_known_item_and_stops_next(
    image_factory, monkeypatch, phase,
):
    sources = [image_factory("first.png"), image_factory("second.png")]
    name = {"flush": "flush_final", "source_close": "close_source", "all_close": "close"}[phase]
    original = getattr(native.DeletionGuard, name)

    def failed(guard):
        original(guard)  # Real work/close first, then an unexpected native-lifetime seam failure.
        raise RuntimeError("PRIVATE_NATIVE_LIFETIME_SENTINEL")

    monkeypatch.setattr(native.DeletionGuard, name, failed)
    result = convert(requested(sources))
    assert result.status == "partial" and result.errors[0].code == "INTERNAL_ERROR", result
    assert result.counts.succeeded == result.counts.published == 1
    assert result.counts.failed == 1 and sources[1].exists()
    first = result.items[0]
    assert first.status == "succeeded" and first.artifact.publication == "verified"
    assert any(w.code == "INTERNAL_ERROR" for w in first.warnings)
    assert first.source_disposition == {
        "flush": "retained", "source_close": "unknown", "all_close": "deleted"
    }[phase]
    assert result.counts.deleted == int(phase == "all_close")
    assert sources[0].exists() is (phase == "flush")
    with assert_image(first.destination):
        pass
    assert not list(sources[0].parent.glob(".ic-*"))


def test_true_has_no_path_source_unlink_shortcut(image_factory, monkeypatch):
    source = image_factory()
    unlink = Path.unlink

    def no_source_unlink(path, *args, **kwargs):
        assert path != source, "Source removal must use the already-held native object."
        return unlink(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", no_source_unlink)
    result = convert(requested([source]))
    assert result.status == "succeeded" and result.counts.deleted == 1 and not source.exists()


@pytest.mark.parametrize("denied", ["intermediate", "source_parent", "output_parent"])
def test_ancestor_list_access_denied_is_pre_staging(image_factory, tmp_path, monkeypatch, denied):
    source = image_factory("inputs/nested/source.png")
    before = source.read_bytes()
    output = tmp_path / "outputs"
    output.mkdir()
    target = {"intermediate": source.parent.parent, "source_parent": source.parent,
              "output_parent": output}[denied]
    opened, attempts = [], []
    native_open = native._Handle.open

    def checked(cls, path, access, share, *, directory=False):
        if directory:
            attempts.append((path, access, share))
            assert access == 129 and share == 3
            if path == target:
                raise ctypes.WinError(5)  # Native open edge fault, not a denied-ACL witness.
        handle = native_open(path, access, share, directory=directory)
        opened.append(handle)
        return handle

    def forbidden(*args, **kwargs):
        pytest.fail("No staging/publication/disposition is allowed after failed ancestor acquire.")

    with monkeypatch.context() as patch:
        patch.setattr(native._Handle, "open", classmethod(checked))
        patch.setattr(fs.Staging, "create", forbidden)
        patch.setattr(fs, "publish_new", forbidden)
        patch.setattr(native.DeletionGuard, "accept_disposition", forbidden)
        result = convert(requested([source], output_directory=output))
    item = result.items[0]
    assert result.status == "failed" and item.status == "failed"
    assert item.error.code == "SOURCE_DELETION_FAILED" and item.error.stage == "source_deletion"
    assert item.source_disposition == "retained" and item.artifact is None
    assert result.counts.published == result.counts.deleted == 0
    assert attempts[-1][0] == target and len([a for a in attempts if a[0] == target]) == 1
    assert opened and all(handle.raw is None for handle in opened)
    assert source.read_bytes() == before and not list(output.iterdir())
    # Same filesystem/permissions, useful non-destructive API control after resource release.
    control = convert(ConversionRequest([source], output_directory=output))
    assert control.status == "succeeded" and control.counts.deleted == 0
    assert source.read_bytes() == before
    with assert_image(control.items[0].destination):
        pass
    source.parent.rename(source.parent.with_name("released-source"))
    output.rename(tmp_path / "released-output")


@pytest.mark.parametrize("confirmation", ["foreign_name", "access_denied"])
def test_post_close_confirmation_never_deletes_foreign_or_infers_denied_absence(
    image_factory, monkeypatch, confirmation,
):
    source = image_factory()
    if confirmation == "foreign_name":
        confirm = native._confirm_deleted

        def replaced(path, identity):
            path.write_bytes(b"NEW_FOREIGN_SOURCE_SENTINEL")
            return confirm(path, identity)

        monkeypatch.setattr(native, "_confirm_deleted", replaced)
    else:
        opened = native._Handle.open

        def denied(cls, path, access, share, *, directory=False):
            if path == source and access == 128 and share == 7:
                raise ctypes.WinError(5)
            return opened(path, access, share, directory=directory)

        monkeypatch.setattr(native._Handle, "open", classmethod(denied))
    result = convert(requested([source]))
    item = result.items[0]
    assert item.status == "succeeded" and item.artifact.publication == "verified"
    with assert_image(item.destination):
        pass
    if confirmation == "foreign_name":
        assert result.status == "succeeded" and result.counts.deleted == 1
        assert item.source_disposition == "deleted"  # Selected object, not the new foreign name.
        assert source.read_bytes() == b"NEW_FOREIGN_SOURCE_SENTINEL"
    else:
        assert result.status == "partial" and result.counts.deleted == 0
        assert item.source_disposition == "unknown" and not source.exists()
        assert item.warnings[0].code == "SOURCE_DELETION_UNCONFIRMED"
