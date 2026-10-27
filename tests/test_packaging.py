"""A real wheel, disposable venv without Qt, and console script outside the repo."""

import importlib.metadata
import json
import os
import shutil
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from .conftest import assert_image
from .image_fixtures import alpha_extrema, write_alpha_png, write_sample_png

REPO = Path(__file__).resolve().parents[1]


def clean_env(cwd):
    env = {
        key: os.environ[key]
        for key in ("SYSTEMROOT", "WINDIR", "PATH", "COMSPEC")
        if key in os.environ
    }
    temporary = cwd / "runtime-temp"
    temporary.mkdir(exist_ok=True)
    env.update(
        PYTHONUTF8="1",
        PYTHONNOUSERSITE="1",
        PIP_DISABLE_PIP_VERSION_CHECK="1",
        TEMP=str(temporary),
        TMP=str(temporary),
        TMPDIR=str(temporary),
        PIP_CACHE_DIR=str(cwd / "pip-cache"),
    )
    return env


def run(command, cwd, log=None, timeout=90, expected_exit=0):
    process = subprocess.run(
        list(map(str, command)), cwd=cwd, env=clean_env(cwd), capture_output=True, timeout=timeout
    )
    if log is not None:
        log.write_bytes(process.stdout + process.stderr + f"\nexit={process.returncode}\n".encode())
        log.with_suffix(".command.json").write_text(
            json.dumps(
                {"argv": list(map(str, command)), "cwd": str(cwd), "exit": process.returncode}
            ),
            encoding="utf-8",
        )
    assert process.returncode == expected_exit, process.stderr.decode("utf-8", errors="replace")
    return process


@pytest.fixture(scope="module")
def installed(tmp_path_factory):
    root = tmp_path_factory.mktemp("installed-wheel")
    source = root / "source-copy"
    source.mkdir()
    # Explicit build input snapshot; do not mutate/reuse historical root build/dist outputs.
    for filename in ("pyproject.toml", "README.md"):
        shutil.copy2(REPO / filename, source / filename)
    for package in ("image_compressor", "gui_pyside6_v2"):
        shutil.copytree(
            REPO / package, source / package, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    wheels = root / "wheels"
    wheels.mkdir()
    run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            source,
            "--no-deps",
            "--no-build-isolation",
            "--wheel-dir",
            wheels,
        ],
        root,
        root / "build.log",
    )
    (wheel,) = wheels.glob("image_compressor-*.whl")
    # Prior wheelhouse is an optional read-only dependency cache, not an output
    # owner. All wheels/venvs/logs from this run stay within its disposable root.
    pillow_wheels = list((REPO / ".agent-work" / "wheels").glob("pillow-*.whl"))
    for pillow_wheel in pillow_wheels:
        shutil.copy2(pillow_wheel, wheels / pillow_wheel.name)
    if not pillow_wheels:
        run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--only-binary=:all:",
                "--no-deps",
                f"Pillow=={importlib.metadata.version('Pillow')}",
                "--dest",
                wheels,
                "--cache-dir",
                root / "pip-cache",
            ],
            root,
            root / "download.log",
        )
    environment = root / "headless-venv"
    run([sys.executable, "-m", "venv", environment], root, root / "venv.log", timeout=90)
    scripts = environment / ("Scripts" if os.name == "nt" else "bin")
    python = scripts / ("python.exe" if os.name == "nt" else "python")
    run(
        [
            python,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            wheels,
            wheel,
        ],
        root,
        root / "install.log",
    )
    outside = root / "outside-repo"
    outside.mkdir()
    return (
        root,
        python,
        scripts / ("image-compressor.exe" if os.name == "nt" else "image-compressor"),
        outside,
        wheel,
    )


@pytest.mark.timeout(240)
def test_wheel_contents_and_installed_no_qt(installed, image_factory):
    root, python, console, outside, wheel = installed
    with zipfile.ZipFile(wheel) as archive:
        names = archive.namelist()
        assert "classes.py" not in names and "gui_main.py" not in names
        assert not any(name.startswith("gui/") for name in names)
        assert "image_compressor/service.py" in names and "image_compressor/py.typed" in names
        assert "gui_pyside6_v2/window.py" in names
        assert "gui_pyside6_v2/tokens.json" in names
        assets = sorted(name for name in names if name.startswith("gui_pyside6_v2/assets/"))
        assert len(assets) == 13 and "gui_pyside6_v2/assets/add.svg" in assets
        assert "gui_pyside6_v2/assets/control-up-dark.svg" in assets
        assert "gui_pyside6_v2/assets/control-check-disabled-light.svg" in assets
        tokens = json.loads(archive.read("gui_pyside6_v2/tokens.json"))
        assert set(tokens["themes"]) == {"light", "dark"}
        assert not any(
            name.startswith(("tools/", ".agent-work/", "tests/", "build/", "dist/"))
            for name in names
        )
        (entry,) = (name for name in names if name.endswith("entry_points.txt"))
        assert b"image-compressor = image_compressor.cli:main" in archive.read(entry)
        (metadata,) = (name for name in names if name.endswith(".dist-info/METADATA"))
        runtime_requires = [
            line
            for line in archive.read(metadata).decode().splitlines()
            if line.startswith("Requires-Dist:") and ";" not in line
        ]
        assert len(runtime_requires) == 1 and "pillow" in runtime_requires[0].lower()
    script = (
        "import importlib.util,json,pathlib,image_compressor; "
        "assert importlib.util.find_spec('PyQt6') is None; "
        "assert importlib.util.find_spec('PySide6') is None; "
        "import gui_pyside6_v2; assert 'PySide6' not in __import__('sys').modules; "
        "assert importlib.util.find_spec('pillow_heif') is None; "
        "assert importlib.util.find_spec('pillow_avif') is None; "
        "print(json.dumps({'module':str(pathlib.Path(image_compressor.__file__).resolve())}))"
    )
    payload = json.loads(run([python, "-I", "-c", script], outside).stdout)
    assert str(root / "headless-venv") in payload["module"]
    optional = run([python, "-I", "-m", "gui_pyside6_v2"], outside, expected_exit=2)
    assert b"gui-pyside6" in optional.stderr and b"Traceback" not in optional.stderr
    assert optional.stdout == b""
    source = image_factory("installed source Юникод.png")
    before = source.read_bytes()
    destination = outside / "installed result.webp"
    process = run(
        [
            console,
            "convert",
            source,
            "--output",
            destination,
            "--max-width",
            "40",
            "--max-height",
            "40",
        ],
        outside,
        root / "console.log",
        timeout=40,
    )
    result = json.loads(process.stdout)
    assert result["status"] == "succeeded" and result["result"]["counts"]["published"] == 1
    assert b"event=conversion_finished" in process.stderr
    with assert_image(destination, size=(40, 30)):
        pass
    assert source.read_bytes() == before
    capabilities = json.loads(run([console, "capabilities"], outside).stdout)
    formats = {item["format"]: item for item in capabilities["result"]["formats"]}
    assert not formats["HEIF"]["encoder_available"] and formats["WEBP"]["roundtrip_verified"]


@pytest.mark.timeout(240)
def test_installed_image_policies(installed):
    root, python, console, outside, _ = installed
    for alpha in (255, 73):
        source = write_alpha_png(outside / f"alpha-{alpha}.png", "rgba", alpha=alpha)
        before = source.read_bytes()
        target = outside / f"alpha-{alpha}.webp"
        process = run(
            [
                console,
                "convert",
                source,
                "--output",
                target,
                "--max-width",
                "12",
                "--max-height",
                "9",
            ],
            outside,
            root / f"alpha-{alpha}.log",
            timeout=40,
        )
        payload = json.loads(process.stdout)
        assert payload["status"] == "succeeded" and payload["result"]["counts"]["published"] == 1
        assert payload["result"]["items"][0]["artifact"]["publication"] == "verified"
        with assert_image(target, size=(12, 9)) as image:
            assert alpha_extrema(image) == (alpha, alpha)
        assert source.read_bytes() == before
    for depth in (8, 16):
        for color_type in (2, 6):
            source = write_sample_png(
                outside / f"samples-{depth}-{color_type}.png", depth=depth, color_type=color_type
            )
            before = source.read_bytes()
            target = source.with_suffix(".webp")
            assert not target.exists()
            process = run(
                [console, "convert", source, "--output", target],
                outside,
                root / f"samples-{depth}-{color_type}.log",
                timeout=40,
                expected_exit=4 if depth == 16 else 0,
            )
            payload = json.loads(process.stdout)
            (item,) = payload["result"]["items"]
            assert item["source_format"] == "PNG"
            if depth == 16:
                assert payload["status"] == "failed"
                assert item["error"]["code"] == "IMAGE_MODE_UNSUPPORTED"
                assert payload["result"]["counts"]["published"] == 0
                assert item["artifact"] is None and not target.exists()
            else:
                assert payload["status"] == "succeeded"
                with assert_image(target, size=(12, 10)) as image:
                    assert alpha_extrema(image) == ((128, 128) if color_type == 6 else (255, 255))
            assert source.read_bytes() == before
    # Direct installed API as well as its console adapter, with no source PYTHONPATH.
    for source_name, succeeds in (("alpha-255.png", True), ("samples-16-2.png", False)):
        source = outside / source_name
        target = outside / (source.stem + "-api.webp")
        script = (
            "import json,sys; from image_compressor import ConversionRequest,convert; "
            "from image_compressor.serialization import to_json; "
            "print(json.dumps(to_json(convert(ConversionRequest([sys.argv[1]],output_path=sys.argv[2])))))"
        )
        process = run(
            [python, "-I", "-B", "-c", script, source, target],
            outside,
            root / (source.stem + "-api.log"),
            timeout=40,
        )
        result = json.loads(process.stdout)
        assert result["status"] == ("succeeded" if succeeds else "failed")
        if succeeds:
            with assert_image(target, size=(24, 18)) as image:
                assert alpha_extrema(image) == (255, 255)
        else:
            assert result["items"][0]["error"]["code"] == "IMAGE_MODE_UNSUPPORTED"
            assert result["counts"]["published"] == 0 and not target.exists()
    assert not list(outside.glob(".ic-*"))


@pytest.mark.timeout(240)
def test_installed_opt_in_deletion_false_refusal_and_native_readbacks(installed, image_factory):
    root, python, console, outside, wheel = installed
    with zipfile.ZipFile(wheel) as archive:
        assert "image_compressor/_windows_deletion.py" in archive.namelist()
    identity = run(
        [python, "-I", "-B", "-c",
         "import importlib.util,importlib.metadata,json,sys; "
         "import image_compressor._windows_deletion as n; "
         "assert n._API is None; "
         "assert importlib.util.find_spec('PyQt6') is None; "
         "assert importlib.util.find_spec('PySide6') is None; "
         "print(json.dumps({'module':n.__file__,'python':sys.version,"
         "'pillow':importlib.metadata.version('Pillow')}))"],
        outside, root / "native-installed-identity.log", timeout=30,
    )
    assert str(root / "headless-venv") in json.loads(identity.stdout)["module"]
    for delete in (False, True):
        source = image_factory(f"installed Кир қаз/source-{delete}.png")
        before = source.read_bytes()
        target = outside / f"résultat-{delete}.webp"
        process = run([console, "convert", source, "--output", target, "--progress",
                       *(["--delete-original"] if delete else [])],
                      outside, root / f"native-{delete}.log", timeout=30)
        payload = json.loads(process.stdout)
        result = payload["result"]
        assert payload["schema_version"] == 1 and result["options"]["delete_original"] is delete
        assert result["counts"]["deleted"] == int(delete)
        assert result["items"][0]["source_disposition"] == ("deleted" if delete else "retained")
        assert result["items"][0]["artifact"]["publication"] == "verified"
        assert source.exists() is (not delete)
        if not delete:
            assert source.read_bytes() == before
        with assert_image(target):
            pass
        assert b"event=conversion_finished" in process.stderr
    source = image_factory("installed readonly.png")
    before = source.read_bytes()
    source.chmod(stat.S_IREAD)
    try:
        process = run([console, "convert", source, "--delete-original"], outside,
                      root / "native-refusal.log", timeout=30, expected_exit=4)
        result = json.loads(process.stdout)["result"]
        assert result["items"][0]["error"]["code"] == "SOURCE_DELETION_FAILED"
        assert result["items"][0]["source_disposition"] == "retained"
        assert result["counts"]["deleted"] == result["counts"]["published"] == 0
        assert source.read_bytes() == before
    finally:
        source.chmod(stat.S_IREAD | stat.S_IWRITE)
    assert not list(source.parent.glob(".ic-*")) and not list(outside.glob(".ic-*"))
