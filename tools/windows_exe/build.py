"""Explicit Windows x64 freezer wrapper. No installation, cleanup or source mutation.

All build inputs are snapshotted before PyInstaller starts. Every build-id is exclusive.
The spec also imports the distribution-owned native/license collectors from this module.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import importlib
import importlib.metadata as metadata
import importlib.util
import json
import os
import re
import shutil
import struct
import subprocess
import sys
import sysconfig
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PACKAGING_FILES = (
    "requirements-win64.txt", "ImageCompressorV2.spec", "frozen_entry.py",
    "ic_frozen_check.py", "build.py",
)
LICENSE_DISTRIBUTIONS = (
    "PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "Pillow",
    "pillow-heif", "pillow-avif-plugin", "PyInstaller",
)


class BuildError(Exception):
    """A closed safe build refusal, not an arbitrary exception projection."""


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def write_json(path: Path, payload: object) -> None:
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def requirement_pins(path: Path) -> dict[str, str]:
    pins: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if not re.fullmatch(r"[A-Za-z0-9_-]+==[0-9][A-Za-z0-9.]*", line):
            raise BuildError("UNPINNED_REQUIREMENT")
        name, version = line.split("==")
        pins[name] = version
    return pins


def owned_distribution_file(dist: metadata.Distribution, item: metadata.PackagePath) -> Path:
    path = Path(str(dist.locate_file(item))).resolve(strict=True)
    if not path.is_relative_to(Path(sys.prefix).resolve()) or not path.is_file():
        raise BuildError("DISTRIBUTION_FILE_OUTSIDE_BUILD_VENV")
    record = item.hash
    if record is None or record.mode != "sha256":
        raise BuildError("NATIVE_OR_LICENSE_RECORD_HASH_MISSING")
    actual = base64.urlsafe_b64encode(bytes.fromhex(digest(path))).rstrip(b"=").decode()
    if actual != record.value:
        raise BuildError("DISTRIBUTION_RECORD_MISMATCH")
    return path


def native_binaries(name: str) -> list[tuple[str, str]]:
    """Only DLLs named in THIS wheel's RECORD. Never glob all site-packages."""
    dist = metadata.distribution(name)
    binaries = []
    for item in dist.files or ():
        if item.suffix.lower() == ".dll":
            source = owned_distribution_file(dist, item)
            # pillow-heif 1.8.1 owns DLLs at site-packages root next to _pillow_heif.
            destination = "." if name == "pillow-heif" else str(item.parent)
            if ".." in Path(destination).parts:
                raise BuildError("UNSAFE_NATIVE_DESTINATION")
            binaries.append((str(source), destination))
    if name == "pillow-heif" and len(binaries) != 6:
        raise BuildError("HEIF_NATIVE_CLOSURE_CHANGED")
    return sorted(binaries)


def license_inputs() -> list[tuple[str, str]]:
    data = []
    for name in LICENSE_DISTRIBUTIONS:
        dist = metadata.distribution(name)
        for item in dist.files or ():
            parts = [part.lower() for part in item.parts]
            basename = item.name.lower()
            if (any("license" in part for part in parts)
                    or basename.startswith(("copying", "notice"))):
                source = Path(str(dist.locate_file(item)))
                if source.is_file():
                    source = owned_distribution_file(dist, item)
                    destination = Path("licenses") / name / item.parent
                    if ".." in destination.parts:
                        raise BuildError("UNSAFE_LICENSE_DESTINATION")
                    data.append((str(source), destination.as_posix()))
    return sorted(set(data))


def minimal_qt_binaries(
    entries: Sequence[tuple[str, str, str]],
) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """Keep Windows/SVG plugins; prune only dependency-unreachable Qt engine DLLs.

    The official QtGui hook also collects optional virtual-keyboard/TUIO/PDF plugins.
    Those drag in QML/Quick/network engines unused by this Widgets adapter. PE import
    and delay-import edges, not a blind DLL blacklist, decide the remaining Qt closure.
    """
    plugins = {"platforms/qwindows.dll", "imageformats/qsvg.dll", "iconengines/qsvgicon.dll"}
    candidates, removed = [], []
    for entry in entries:
        name = entry[0].replace("\\", "/").lower()
        if "/plugins/" in name and name.split("/plugins/", 1)[1] not in plugins:
            removed.append(entry)
        else:
            candidates.append(entry)
    by_name: dict[str, list[int]] = {}
    for index, entry in enumerate(candidates):
        by_name.setdefault(Path(entry[0]).name.lower(), []).append(index)
    pefile = importlib.import_module("pefile")  # Pinned PyInstaller build dependency, not runtime.
    reached: set[int] = set()
    roots = [index for index, entry in enumerate(candidates)
             if not entry[0].replace("\\", "/").startswith("PySide6/")
             or entry[2] == "EXTENSION" or "/plugins/" in entry[0].replace("\\", "/")]
    pending = list(roots)
    while pending:
        index = pending.pop()
        if index in reached:
            continue
        reached.add(index)
        source = candidates[index][1]
        pe = pefile.PE(source, fast_load=True)
        try:
            pe.parse_data_directories(directories=[1, 13])  # IMPORT and DELAY_IMPORT.
            imports = {item.dll.decode("ascii").lower()
                       for attribute in ("DIRECTORY_ENTRY_IMPORT", "DIRECTORY_ENTRY_DELAY_IMPORT")
                       for item in getattr(pe, attribute, ())}
        finally:
            pe.close()
        for dependency in imports:
            pending.extend(by_name.get(dependency, ()))
    kept = []
    for index, entry in enumerate(candidates):
        name = Path(entry[0]).name.lower()
        if index not in reached and (name.startswith("qt6") or name.startswith("pyside6qml.")):
            removed.append(entry)
        else:
            kept.append(entry)
    return kept, removed


def analysis_manifest(
    path: Path, binaries: Sequence[tuple[str, str, str]],
    datas: Sequence[tuple[str, str, str]], pure: Sequence[tuple[str, str, str]],
    removed_qt: Sequence[tuple[str, str, str]] = (),
) -> None:
    records = {}
    for label, entries in (("binaries", binaries), ("datas", datas), ("pure", pure),
                           ("removed_optional_qt", removed_qt)):
        records[label] = [
            {"destination": dst.replace("\\", "/"), "source": src, "kind": kind,
             "sha256": digest(Path(src)) if Path(src).is_file() else None}
            for dst, src, kind in entries
        ]
    write_json(path, records)


def prepare_paths(root: Path, build_id: str) -> tuple[Path, Path]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", build_id):
        raise BuildError("INVALID_BUILD_ID")
    work = root / ".agent-work/windows-exe/builds" / build_id
    output = root / "dist/windows-pyside6" / build_id
    if work.exists() or output.exists():
        raise BuildError("BUILD_ROOT_OCCUPIED")
    work.mkdir(parents=True, exist_ok=False)
    output.mkdir(parents=True, exist_ok=False)
    return work, output


def input_files(root: Path) -> list[Path]:
    files = [root / "pyproject.toml", root / "README.md"]
    for package in ("image_compressor", "gui_pyside6_v2"):
        files.extend(path for path in (root / package).rglob("*")
                     if path.is_file() and path.suffix in (".py", ".json", ".svg", ".typed"))
    files.extend(root / "tools/windows_exe" / name for name in PACKAGING_FILES)
    return sorted(files)


def validate_toolchain(root: Path) -> dict[str, str]:
    if (sys.implementation.name != "cpython" or sys.platform != "win32"
            or struct.calcsize("P") != 8 or sysconfig.get_platform() != "win-amd64"
            or sys.version_info[:3] != (3, 14, 2)):
        raise BuildError("REQUIRES_CPYTHON_3_14_2_WINDOWS_X64")
    if Path(sys.prefix).resolve() != (root / ".agent-work/windows-exe/build-venv").resolve():
        raise BuildError("USE_THE_NEW_PROJECT_BUILD_VENV")
    for binding in ("PyQt6", "PyQt5", "PySide2"):
        if importlib.util.find_spec(binding) is not None:
            raise BuildError("FOREIGN_QT_BINDING_PRESENT")
    pins = requirement_pins(root / "tools/windows_exe/requirements-win64.txt")
    for name, expected in pins.items():
        if metadata.version(name) != expected:
            raise BuildError("TOOLCHAIN_VERSION_MISMATCH")
    return pins


def archive_names(executable: Path) -> list[str]:
    # Build-time API only; the frozen product never imports PyInstaller.
    reader_module = importlib.import_module("PyInstaller.archive.readers")
    reader = reader_module.CArchiveReader(str(executable))
    return sorted(str(name).replace("\\", "/") for name in reader.toc)


def verify_archive(names: Sequence[str], root: Path, work: Path) -> None:
    assets = sorted(path.name for path in (root / "gui_pyside6_v2/assets").glob("*.svg"))
    if not assets:
        raise BuildError("REQUIRED_FROZEN_RESOURCE_MISSING")
    required = tuple(f"gui_pyside6_v2/assets/{name}" for name in assets) + (
        "gui_pyside6_v2/tokens.json", "python314.dll",
    )
    if any(name not in names for name in required):
        raise BuildError("REQUIRED_FROZEN_RESOURCE_MISSING")
    lowered = [name.lower() for name in names]
    pure = {
        entry["destination"]
        for entry in json.loads((work / "analysis.json").read_text(encoding="utf-8"))["pure"]
    }
    if "image_compressor._windows_deletion" not in pure:
        raise BuildError("REQUIRED_DELETION_MODULE_MISSING")
    legacy_exact = ("classes", "classes.py", "gui_main", "gui_main.py")
    legacy_prefixes = ("gui/", "classes/", "gui_main/")
    if any(name in legacy_exact or name.startswith(legacy_prefixes) for name in lowered):
        raise BuildError("LEGACY_RUNTIME_BUNDLED")
    if not any(name.endswith("/platforms/qwindows.dll") for name in names):
        raise BuildError("WINDOWS_PLATFORM_PLUGIN_MISSING")
    if not any(name.startswith("_pillow_heif.") and name.endswith(".pyd") for name in names):
        raise BuildError("TOP_LEVEL_HEIF_EXTENSION_MISSING")
    if not any("pillow_avif/_avif" in name and name.endswith(".pyd") for name in names):
        raise BuildError("AVIF_FALLBACK_NOT_PACKAGED")
    if not any("vcruntime140" in name.lower() for name in names):
        raise BuildError("VC_RUNTIME_MISSING")
    denied = ("pyqt", "qt6qml", "qt6quick", "qt6webengine", "qt6pdf", "pyside6/qttest", "tkinter",
              "figcraft", "tests_windows_exe", "tests_pyside6_v2")
    if any(any(fragment in name.lower() for fragment in denied) for name in names):
        raise BuildError("UNRELATED_RUNTIME_BUNDLED")


def build(root: Path, build_id: str, *, mode: str, fallback_reason: str | None) -> Path:
    if mode not in ("onefile", "onedir") or (mode == "onedir" and not fallback_reason):
        raise BuildError("ONEDIR_REQUIRES_DIAGNOSED_FALLBACK_REASON")
    versions = validate_toolchain(root)
    work, output = prepare_paths(root, build_id)
    snapshot = work / "inputs"
    snapshot.mkdir()
    inputs = {}
    for source in input_files(root):
        relative = source.relative_to(root)
        destination = snapshot / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        inputs[relative.as_posix()] = digest(destination)
    wheelhouse = root / ".agent-work/windows-exe/wheelhouse"
    wheels = {path.name: digest(path) for path in sorted(wheelhouse.glob("*.whl"))}
    if not wheels:
        raise BuildError("PINNED_WHEELHOUSE_REQUIRED")
    write_json(work / "frozen-inputs.json", {"inputs": inputs, "wheels": wheels,
                                           "toolchain": versions, "python": sys.version})
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith(("PYTHON", "QT", "QML", "_PYI_"))}
    for name in ("temp", "cache"):
        (work / name).mkdir()
    windows = Path(os.environ["SYSTEMROOT"])
    env.update(PATH=os.pathsep.join(map(str, (Path(sys.executable).parent,
                                              windows / "System32", windows))),
               TEMP=str(work / "temp"), TMP=str(work / "temp"), TMPDIR=str(work / "temp"),
               PYINSTALLER_CONFIG_DIR=str(work / "cache"), PYTHONDONTWRITEBYTECODE="1",
               IC_WINDOWS_EXE_MODE=mode, IC_EXE_ANALYSIS_RECEIPT=str(work / "analysis.json"))
    command = [sys.executable, "-I", "-B", "-m", "PyInstaller",
               str(snapshot / "tools/windows_exe/ImageCompressorV2.spec"),
               "--workpath", str(work / "pyinstaller"), "--distpath", str(output),
               "--noconfirm"]
    write_json(work / "command.json", {
        "argv": command, "cwd": str(work),
        "environment_policy": "local cache/temp; build venv + Windows PATH; no Qt overrides",
    })
    started = time.monotonic()
    with (work / "stdout.txt").open("xb") as stdout, (work / "stderr.txt").open("xb") as stderr:
        process = subprocess.Popen(command, cwd=work, env=env, stdout=stdout, stderr=stderr)
        try:
            code = process.wait(timeout=108)
        except subprocess.TimeoutExpired:
            # Only this still-owned process tree, never kill by executable name.
            taskkill = Path(os.environ["SYSTEMROOT"]) / "System32/taskkill.exe"
            subprocess.run([str(taskkill), "/PID", str(process.pid), "/T", "/F"],
                           capture_output=True, timeout=5, check=False)
            process.wait(timeout=5)
            code = 124
    write_json(work / "process-result.json", {"pid": process.pid, "exit": code,
                                             "elapsed_seconds": time.monotonic()-started})
    if code:
        raise BuildError("PYINSTALLER_FAILED")
    executable = output / ("ImageCompressorV2.exe" if mode == "onefile"
                           else "ImageCompressorV2/ImageCompressorV2.exe")
    names = archive_names(executable)
    if mode == "onefile":
        verify_archive(names, root, work)
    else:
        names += [path.relative_to(executable.parent / "_internal").as_posix()
                  for path in (executable.parent / "_internal").rglob("*") if path.is_file()]
        verify_archive(names, root, work)
    write_json(work / "archive-inventory.json", names)
    reader = importlib.import_module("PyInstaller.archive.readers").CArchiveReader(str(executable))
    payload_hashes = {name: hashlib.sha256(reader.extract(name)).hexdigest()
                      for name in reader.toc if name.lower().endswith((".dll", ".pyd"))}
    write_json(work / "payload-hashes.json", payload_hashes)
    notices = output / "notices"
    for source_name, destination_name in license_inputs():
        source = Path(source_name)
        relative = Path(destination_name).relative_to("licenses") / source.name
        target = notices / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    (notices / "CPython").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(python_license, notices / "CPython/LICENSE.txt")
    readme = (
        "ImageCompressorV2 — Windows x64 / " + mode + "\n"
        "Double-click ImageCompressorV2.exe; no external Python/Qt install is required.\n"
        "One-file extracts to owned user TEMP while running. Keep originals; no overwrite/delete.\n"
        "Unsigned local artifact; do not disable Windows security. See dependency notices.\n"
        "Build and exact-byte verification: docs/figcraft_gui_experiment/WINDOWS_EXE.md\n"
    )
    (output / "README.txt").write_text(readme, encoding="utf-8")
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                            capture_output=True, check=True).stdout.decode()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root,
                          capture_output=True, check=True).stdout.decode().strip()
    info: dict[str, Any] = {
        "status": "built_not_independently_accepted", "build_id": build_id, "mode": mode,
        "fallback_reason": fallback_reason, "source_head": head, "source_delta": status,
        "interpreter": sys.executable, "python": sys.version, "toolchain": versions,
        "inputs": inputs, "wheel_sha256": wheels, "command": command,
        "executable": str(executable), "bytes": executable.stat().st_size,
        "sha256": digest(executable), "build_work": str(work),
        "payload_sha256": payload_hashes,
        "notices": [path.relative_to(output).as_posix() for path in sorted(notices.rglob("*"))
                    if path.is_file()],
    }
    write_json(output / "BUILD-INFO.json", info)
    if mode == "onedir":
        shutil.make_archive(str(output / "ImageCompressorV2-portable"), "zip", executable.parent)
    return executable


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-id", required=True)
    parser.add_argument("--mode", choices=("onefile", "onedir"), default="onefile")
    parser.add_argument("--fallback-reason")
    args = parser.parse_args()
    try:
        executable = build(ROOT, args.build_id, mode=args.mode,
                           fallback_reason=args.fallback_reason)
    except (BuildError, OSError, metadata.PackageNotFoundError) as exc:
        reason = str(exc) if isinstance(exc, BuildError) else "BUILD_IO_OR_DEPENDENCY_ERROR"
        print("BUILD_FAILED: " + reason, file=sys.stderr)
        return 1
    print(json.dumps({"executable": str(executable), "sha256": digest(executable)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
