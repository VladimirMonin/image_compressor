import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from image_compressor import ConversionRequest, convert, discover_inputs, discovery
from image_compressor import filesystem as fs


def test_order_recursive_aliases_and_hardlinks(image_factory, tmp_path, monkeypatch):
    z = image_factory("tree/z.PNG")
    a = image_factory("tree/A.jpg")
    nested = image_factory("tree/sub/b.webp")
    hardlink = tmp_path / "physical.png"
    os.link(a, hardlink)
    ignored = tmp_path / "tree" / "note.txt"
    ignored.write_bytes(b"IGNORED")
    monkeypatch.chdir(tmp_path)
    result = discover_inputs(["tree", z, str(a.absolute()), hardlink, "tree"], recursive=True)
    assert result.paths == (a, nested, z)
    assert result.duplicates == 6 and result.ignored == 2
    assert result.discovery_complete and not result.errors and not result.issues
    shallow = discover_inputs([tmp_path / "tree"], recursive=False)
    assert shallow.paths == (a, z)
    assert shallow.ignored == 1


def test_fixed_manifest_output_child_and_same_root(image_factory, tmp_path):
    source = image_factory("input/source.png")
    child = tmp_path / "input" / "out"
    child.mkdir()
    image_factory("input/out/prior.png")
    discovery_result = discover_inputs([source.parent], recursive=True, exclude_directory=child)
    assert discovery_result.paths == (source,)
    result = convert(ConversionRequest([source.parent], recursive=True, output_directory=child))
    assert result.status == "succeeded" and result.counts.total == 1
    same = discover_inputs([source.parent], recursive=False, exclude_directory=source.parent)
    assert same.paths == (source,)
    # A created result was not incorporated into the already frozen manifest.
    assert [item.source for item in result.items] == [source]


def test_missing_unsupported_and_mixed_partial(image_factory, tmp_path):
    good = image_factory()
    missing = tmp_path / "missing.png"
    unsupported = tmp_path / "explicit.txt"
    unsupported.write_bytes(b"IGNORED_CONTENT")
    result = convert(ConversionRequest([missing, good, unsupported]))
    assert result.status == "partial"
    assert [i.source for i in result.items] == [missing, good, unsupported]
    assert [i.error.code if i.error else None for i in result.items] == [
        "INPUT_NOT_FOUND",
        None,
        "UNSUPPORTED_INPUT_EXTENSION",
    ]
    assert result.counts.failed == 2 and result.counts.succeeded == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    rejected = convert(ConversionRequest([empty]))
    assert rejected.status == "rejected" and rejected.errors[0].code == "NO_INPUTS"


def test_controlled_directory_failure_visible(image_factory, tmp_path, monkeypatch):
    source = image_factory("root/source.png")
    denied = tmp_path / "root" / "denied"
    denied.mkdir()
    original = discovery._directory_children

    def read(path):
        if path == denied:
            raise PermissionError("PRIVATE_DIRECTORY_EXCEPTION")
        return original(path)

    monkeypatch.setattr(discovery, "_directory_children", read)
    result = convert(ConversionRequest([source.parent], recursive=True))
    assert result.status == "partial"
    assert [i.source for i in result.items] == [denied, source]
    assert result.items[0].error.code == "DIRECTORY_READ_FAILED"


def test_reparse_branch_without_symlink_privileges(image_factory, monkeypatch):
    source = image_factory()
    original = Path.lstat

    def reparse(path, *args, **kwargs):
        value = original(path, *args, **kwargs)
        if path == source:
            return SimpleNamespace(st_mode=value.st_mode, st_file_attributes=1024)
        return value

    monkeypatch.setattr(Path, "lstat", reparse)
    # Force the Windows reparse bit even on platforms without that stat constant.
    monkeypatch.setattr(fs.stat, "FILE_ATTRIBUTE_REPARSE_POINT", 1024, raising=False)
    result = discover_inputs([source])
    assert result.paths == () and result.issues[0].error.code == "UNSAFE_PATH"


def test_real_symlink_and_no_traversal(image_factory, tmp_path):
    source = image_factory("outside/source.png")
    selected = tmp_path / "selected"
    selected.mkdir()
    link = selected / "link"
    try:
        link.symlink_to(source.parent, target_is_directory=True)
    except OSError as exc:
        pytest.skip(
            f"Native symlink privilege unavailable (winerror={getattr(exc, 'winerror', None)})"
        )
    nested = discover_inputs([selected], recursive=True)
    assert nested.paths == () and nested.ignored == 1
    assert nested.warnings[0].code == "UNSAFE_PATH"
    explicit = discover_inputs([link])
    assert explicit.issues[0].error.code == "UNSAFE_PATH"
    ancestor = discover_inputs([link / source.name])
    assert ancestor.issues[0].error.code == "UNSAFE_PATH"
    hidden = discover_inputs([link / ".." / "source.png"])
    assert hidden.issues[0].error.code == "UNSAFE_PATH"
