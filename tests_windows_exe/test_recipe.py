"""Static/guard checks for the NEW freezer recipe; collection must not import Qt."""
import ast
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
RECIPE = REPO / "tools/windows_exe"


def test_required_recipe_inputs_exist():
    required = (
        "requirements-win64.txt", "ImageCompressorV2.spec", "frozen_entry.py",
        "ic_frozen_check.py", "build.py",
    )
    missing = [name for name in required if not (RECIPE / name).is_file()]
    assert not missing, f"The authorized standalone EXE recipe is missing: {missing}"


def load_recipe(name):
    spec = importlib.util.spec_from_file_location(f"recipe_{name}", RECIPE / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_collection_and_guards_do_not_import_qt():
    load_recipe("build")
    load_recipe("frozen_entry")
    load_recipe("ic_frozen_check")
    assert not any(name.startswith(("PySide6", "PyQt6")) for name in sys.modules)


def test_pins_and_static_recipe_boundary():
    builder = load_recipe("build")
    pins = builder.requirement_pins(RECIPE / "requirements-win64.txt")
    assert len(pins) == 16
    assert pins["PyInstaller"] == "6.18.0" and pins["Pillow"] == "13.0.0"
    assert pins["pillow-heif"] == "1.8.1" and pins["pillow-avif-plugin"] == "1.6.0"
    assert not any(name.lower().startswith("pyqt") for name in pins)
    spec = (RECIPE / "ImageCompressorV2.spec").read_text(encoding="utf-8")
    ast.parse(spec)
    for required in ("console=False", "upx=False", "strip=False", "optimize=0",
                     "runtime_tmpdir=None", "disable_windowed_traceback=True",
                     '"_pillow_heif"', '"pillow_avif._avif"', "tokens.json",
                     "gui_pyside6_v2/assets"):
        assert required in spec
    assert 'glob("*.svg")' in spec
    assert "collect_all" not in spec and "gui_main.py" not in spec
    driver = (RECIPE / "ic_frozen_check.py").read_text(encoding="utf-8")
    imports = [node for node in ast.walk(ast.parse(driver))
               if isinstance(node, (ast.Import, ast.ImportFrom))]
    names = {alias.name for node in imports if isinstance(node, ast.Import)
             for alias in node.names}
    names.update(node.module for node in imports if isinstance(node, ast.ImportFrom))
    assert not names.intersection({"runpy", "subprocess", "tests", "tests_pyside6_v2"})
    for prohibited in ("sys.path.insert", "sys.path.append", "monkeypatch", "exec(", "eval("):
        assert prohibited not in driver
    for required in ("gui_main([sys.executable])", "start_button.click()", "window.add_paths"):
        assert required in driver


@pytest.mark.parametrize("build_id", ("", "../escape", "bad/name", "bad name", "a" * 65))
def test_build_id_refusal_has_no_effects(tmp_path, build_id):
    builder = load_recipe("build")
    with pytest.raises(builder.BuildError, match="INVALID_BUILD_ID"):
        builder.prepare_paths(tmp_path, build_id)
    assert list(tmp_path.iterdir()) == []


def test_build_root_collision_preserves_prior_bytes(tmp_path):
    builder = load_recipe("build")
    work, output = builder.prepare_paths(tmp_path, "safe-build-01")
    prior = output / "ImageCompressorV2.exe"
    prior.write_bytes(b"owned synthetic prior artifact")
    with pytest.raises(builder.BuildError, match="BUILD_ROOT_OCCUPIED"):
        builder.prepare_paths(tmp_path, "safe-build-01")
    assert work.is_dir() and prior.read_bytes() == b"owned synthetic prior artifact"
    with pytest.raises(builder.BuildError, match="ONEDIR_REQUIRES"):
        builder.build(tmp_path, "must-not-exist", mode="onedir", fallback_reason=None)
    assert not (tmp_path / "dist/windows-pyside6/must-not-exist").exists()


@pytest.mark.parametrize("arguments", (("--unknown",), ("--packaging-check",),
                                      ("--packaging-check", "x", "extra")))
def test_launcher_rejects_unknown_arguments_without_qt(arguments):
    entry = load_recipe("frozen_entry")
    assert entry.main(arguments) == 2
    assert "ic_frozen_check" not in sys.modules


@pytest.mark.parametrize("raw", ("relative", "C:relative", r"\\server\share\new",
                                 r"\\?\C:\new", "C:/unsafe\0new"))
def test_output_rejects_nonlocal_or_relative_before_io(raw):
    guard = load_recipe("ic_frozen_check")
    with pytest.raises(ValueError):
        guard.checked_output_path(raw, ())


def test_output_is_exclusive_and_separated_from_runtime(tmp_path):
    guard = load_recipe("ic_frozen_check")
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    target = tmp_path / "fresh-check"
    assert guard.checked_output_path(str(target), (runtime,)) == target
    assert not target.exists()
    with pytest.raises(ValueError, match="OUTPUT_OVERLAPS_RUNTIME"):
        guard.checked_output_path(str(runtime / "inside"), (runtime,))
    occupied = tmp_path / "occupied"
    occupied.mkdir()
    prior = occupied / "sentinel"
    prior.write_bytes(b"must survive")
    with pytest.raises(ValueError, match="OUTPUT_OCCUPIED"):
        guard.checked_output_path(str(occupied), (runtime,))
    assert prior.read_bytes() == b"must survive"


def test_output_rejects_real_owned_windows_junction(tmp_path):
    assert sys.platform == "win32", "This recipe is Windows-only"
    guard = load_recipe("ic_frozen_check")
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "junction"
    command = [os.environ["COMSPEC"], "/d", "/c", "mklink", "/J", str(link), str(real)]
    result = subprocess.run(command, capture_output=True, timeout=5, check=False)
    assert result.returncode == 0, result.stderr
    with pytest.raises(ValueError, match="UNSAFE_OUTPUT_PARENT"):
        guard.checked_output_path(str(link / "new-check"), ())
    assert list(real.iterdir()) == []
