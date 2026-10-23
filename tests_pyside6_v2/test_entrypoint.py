"""Separate binding processes and the lazy optional package boundary."""

import hashlib
import json
import os
import subprocess
from pathlib import Path

from gui_pyside6_v2.theme import TOKENS

REPO = Path(__file__).resolve().parents[1]
LEGACY = REPO / ".venv/Scripts/python.exe"


def test_optional_package_is_lazy_and_error_is_safe_without_pyside(tmp_path):
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    script = (
        "import sys,importlib.util,gui_pyside6_v2; "
        "assert not any(k.startswith(('PyQt6','PySide6')) for k in sys.modules); "
        "assert importlib.util.find_spec('PySide6') is None; "
        "from gui_pyside6_v2.__main__ import main; raise SystemExit(main())"
    )
    process = subprocess.run(
        [str(LEGACY), "-B", "-c", script],
        cwd=REPO,
        env=env,
        capture_output=True,
        timeout=30,
    )
    assert process.returncode == 2
    assert b"gui-pyside6" in process.stderr and b"Traceback" not in process.stderr
    assert process.stdout == b""


def test_existing_binding_is_rejected_before_second_binding_import(tmp_path):
    script = (
        "import sys,PyQt6; from gui_pyside6_v2.__main__ import main; "
        "code=main(); assert not any(k.startswith('PySide6') for k in sys.modules); "
        "raise SystemExit(code)"
    )
    process = subprocess.run(
        [str(LEGACY), "-B", "-c", script],
        cwd=REPO,
        capture_output=True,
        timeout=30,
    )
    assert process.returncode == 2
    assert b"separate process" in process.stderr and b"Traceback" not in process.stderr


def test_runtime_tokens_match_real_engine_variable_export():
    native = REPO / "design/figcraft/image-compressor-v2.figcraft"
    assert hashlib.sha256(native.read_bytes()).hexdigest() == TOKENS["source"]["native_sha256"]
    raw = json.loads((REPO / "design/figcraft/variables.raw.json").read_text(encoding="utf-8"))
    variables = raw["meta"]["variables"].values()
    collection = next(
        collection
        for collection in raw["meta"]["variableCollections"].values()
        if collection["name"] == "Theme"
    )
    for mode in collection["modes"]:
        theme = TOKENS["themes"][mode["name"].lower()]
        for variable in variables:
            if variable["name"] in theme:
                value = variable["valuesByMode"][mode["modeId"]]
                color = "#" + "".join(f"{round(value[channel] * 255):02X}" for channel in "rgb")
                assert color == theme[variable["name"]]
