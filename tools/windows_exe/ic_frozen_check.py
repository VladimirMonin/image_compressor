"""Opt-in, synthetic-only qualification of THIS frozen GUI, never a second converter.

No source path injection, runpy, arbitrary scripts/config/inputs or network entry points.
Pure path guards run before Qt imports and before creating the exclusive owned output root.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import stat
import sys
from ctypes import wintypes
from dataclasses import asdict
from importlib.resources import files
from pathlib import Path
from typing import Any


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def checked_output_path(raw: str, forbidden: tuple[Path, ...]) -> Path:
    path = Path(raw)
    if (not path.is_absolute() or len(path.drive) != 2 or path.drive[1] != ":"
            or not path.drive[0].isalpha() or "\0" in raw):
        raise ValueError("ABSOLUTE_LOCAL_PATH_REQUIRED")
    for part in path.parts[1:]:
        if part in (".", "..") or part.endswith((".", " ")) or ":" in part:
            raise ValueError("UNSAFE_OUTPUT_COMPONENT")
    try:
        path.lstat()
    except FileNotFoundError:
        pass
    else:
        raise ValueError("OUTPUT_OCCUPIED")
    for ancestor in (path.parent, *path.parent.parents):
        value = ancestor.lstat()
        if (not stat.S_ISDIR(value.st_mode) or stat.S_ISLNK(value.st_mode)
                or getattr(value, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError("UNSAFE_OUTPUT_PARENT")
    for boundary in forbidden:
        boundary = boundary.resolve(strict=True)
        if path == boundary or path.is_relative_to(boundary) or boundary.is_relative_to(path):
            raise ValueError("OUTPUT_OVERLAPS_RUNTIME")
    return path


def loaded_libraries(bundle: Path) -> list[dict[str, str]]:
    """Actual process native provenance, not only package presence or a claimed probe."""
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.EnumProcessModulesEx.argtypes = [wintypes.HANDLE, ctypes.c_void_p,
                                          wintypes.DWORD, ctypes.POINTER(wintypes.DWORD),
                                          wintypes.DWORD]
    psapi.EnumProcessModulesEx.restype = wintypes.BOOL
    psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
                                          wintypes.LPWSTR, wintypes.DWORD]
    psapi.GetModuleFileNameExW.restype = wintypes.DWORD
    process = kernel.GetCurrentProcess()
    handles = (wintypes.HMODULE * 2048)()
    needed = wintypes.DWORD()
    if not psapi.EnumProcessModulesEx(process, handles, ctypes.sizeof(handles),
                                     ctypes.byref(needed), 3):
        raise RuntimeError("NATIVE_INVENTORY_FAILED")
    if needed.value > ctypes.sizeof(handles):
        raise RuntimeError("NATIVE_INVENTORY_TRUNCATED")
    windows = Path(os.environ["SYSTEMROOT"]).resolve()
    executable = Path(sys.executable).resolve()
    records = []
    for handle in handles[:needed.value // ctypes.sizeof(wintypes.HMODULE)]:
        buffer = ctypes.create_unicode_buffer(32768)
        if not psapi.GetModuleFileNameExW(process, handle, buffer, len(buffer)):
            raise RuntimeError("NATIVE_PATH_UNAVAILABLE")
        path = Path(buffer.value).resolve(strict=True)
        if path == executable:
            origin = "self"
        elif path.is_relative_to(bundle):
            origin = "bundle"
        elif path.is_relative_to(windows):
            origin = "windows"
        else:
            raise RuntimeError("EXTERNAL_NATIVE_DEPENDENCY")
        records.append({"path": str(path), "origin": origin,
                        "sha256": digest(path) if origin != "windows" else "system"})
    return records


def run(raw_output: str) -> int:
    if sys.platform != "win32" or not getattr(sys, "frozen", False):
        return 2
    bundle = Path(getattr(sys, "_MEIPASS")).resolve(strict=True)
    executable = Path(sys.executable).resolve(strict=True)
    try:
        root = checked_output_path(raw_output, (bundle, executable.parent))
        root.mkdir(exist_ok=False)
        # Recheck after creation: only a real fresh directory is ours.
        value = root.lstat()
        if getattr(value, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT:
            return 2
    except (OSError, ValueError):
        return 2

    receipt: dict[str, Any] = {
        "schema_version": 1, "status": "failed", "reason": "CHECK_NOT_FINISHED",
        "frozen": True, "executable": str(executable), "exe_sha256": digest(executable),
        "bundle": str(bundle), "pid": os.getpid(), "parent_pid": os.getppid(),
        "start_actions": 0, "requests": [], "screens": [], "cases": [],
    }
    try:
        import PIL
        import PySide6
        from PIL import Image
        from PySide6.QtCore import QByteArray, Qt, QTimer
        from PySide6.QtGui import QFontInfo, QRawFont
        from PySide6.QtSvg import QSvgRenderer
        from PySide6.QtWidgets import QApplication

        from gui_pyside6_v2.__main__ import main as gui_main
        from gui_pyside6_v2.window import MainWindow
        from image_compressor import BatchResult
        from image_compressor import _windows_deletion as native_deletion

        if QApplication.instance() is not None:
            raise RuntimeError("UNEXPECTED_EXISTING_APPLICATION")
        app = QApplication([sys.executable])
        receipt["versions"] = {"python": sys.version, "PySide6": PySide6.__version__,
                               "Pillow": PIL.__version__}
        receipt["platform"] = app.platformName()
        if app.platformName() != "windows":
            raise RuntimeError("WINDOWS_QPA_REQUIRED")
        data_root = files("gui_pyside6_v2")
        asset_root = data_root.joinpath("assets")
        asset_names = sorted(path.name for path in asset_root.iterdir()
                             if path.name.endswith(".svg"))
        if len(asset_names) != 13 or "add.svg" not in asset_names:
            raise RuntimeError("SVG_SET_INCOMPLETE")
        resource_names = ["tokens.json"] + [f"assets/{name}" for name in asset_names]
        receipt["resources"] = {
            name: {"path": str(data_root.joinpath(name)),
                   "sha256": hashlib.sha256(data_root.joinpath(name).read_bytes()).hexdigest()}
            for name in resource_names
        }
        for name in asset_names:
            svg = QSvgRenderer(QByteArray(asset_root.joinpath(name).read_bytes()))
            if not svg.isValid():
                raise RuntimeError("SVG_INVALID")
        forbidden_exact = {"gui", "classes", "gui_main"}
        receipt["deletion_module_loaded"] = native_deletion.__name__ in sys.modules
        receipt["deletion_available"] = bool(native_deletion.available())
        if not receipt["deletion_module_loaded"]:
            raise RuntimeError("DELETION_MODULE_MISSING")
        forbidden_loaded = sorted(
            name for name in sys.modules
            if name in forbidden_exact or name.startswith(("gui.", "classes.", "gui_main."))
        )
        if forbidden_loaded:
            raise RuntimeError("FORBIDDEN_MODULES_LOADED")
        receipt["forbidden_modules_absent"] = True
        inputs = root / "inputs"
        inputs.mkdir()
        source = inputs / "synthetic_ӘҒҚҢӨҰҮҺІ.png"
        with Image.new("RGB", (400, 300), (27, 143, 201)) as image:
            image.save(source)
        initial = digest(source)
        sources = {source: initial}
        receipt["sources"] = [{"path": str(source.relative_to(root)), "sha256": initial}]

        class Driver:
            def __init__(self) -> None:
                self.window: MainWindow | None = None
                self.phase = "capabilities"
                self.screen = 0
                self.codec = 0
                self.done = False
                self.failed = False
                self.failure = "CHECK_FAILED"
                self.prior_webp = ""
                self.formats = (("WEBP", 1), ("JPEG", 0), ("HEIF", 2), ("AVIF", 3))
                self.delete_source = Path()
                self.keep_source = Path()
                self.partial_good = Path()
                self.partial_bad = Path()
                self.delete_expected = ""
                self.keep_expected = ""
                self.partial_bad_expected = ""

            def fail(self, reason: str) -> None:
                self.failed = True
                self.failure = reason
                timer.stop()
                if self.window is not None:
                    self.window.close()  # The unchanged close handler waits for real workers.
                else:
                    app.quit()

            def presentation(self) -> None:
                assert self.window is not None
                language, theme = divmod(self.screen, 2)
                self.window.locale_combo.setCurrentIndex(language)
                self.window.theme_combo.setCurrentIndex(theme)
                self.window.resize(900, 640) if self.screen == 5 else self.window.resize(1120, 760)

            def capture(self) -> None:
                assert self.window is not None
                window = self.window
                assert window.isVisible() and window.windowHandle().isExposed()
                assert window.settings.delete_original.isEnabled()
                assert not window.settings.delete_original.isChecked()
                assert window.settings.delete_original.text()
                assert window.settings.safety_explanation.isVisible()
                font = QFontInfo(window.font())
                raw_font = QRawFont.fromFont(window.font())
                glyphs = "ӘҒҚҢӨҰҮҺІәғқңөұүһі"
                assert all(raw_font.supportsCharacter(ord(char)) for char in glyphs)
                assert font.family() == "Segoe UI"
                icon = window.add_button.icon().pixmap(24, 24).toImage()
                assert not icon.isNull()
                assert sum(icon.pixelColor(x, y).alpha() > 20
                           for x in range(icon.width()) for y in range(icon.height())) > 10
                name = f"{window.language}-{window.theme}.png"
                output = root / name
                pixmap = window.grab()
                assert pixmap.save(str(output))
                receipt["screens"].append({
                    "path": name, "sha256": digest(output), "locale": window.language,
                    "theme": window.theme, "logical_size": [window.width(), window.height()],
                    "png_size": [pixmap.width(), pixmap.height()],
                    "dpr": window.devicePixelRatioF(),
                    "requested_font": window.font().family(), "resolved_font": font.family(),
                    "glyphs_verified": glyphs, "svg_visible": True,
                })

            def start(self, index: int, *, delete: bool = False) -> None:
                assert self.window is not None
                window = self.window
                window.settings.output_format.setCurrentIndex(index)
                assert window.start_button.isEnabled()
                receipt["start_actions"] += 1
                window.start_button.click()
                assert window.controller.worker is not None
                request = window.controller.request_snapshot
                assert request is not None and request.delete_original is delete
                assert request.quality == 80
                assert (request.max_width, request.max_height) == (192, 108)
                receipt["requests"].append({"output_format": request.output_format,
                                             "quality": request.quality,
                                             "max_width": request.max_width,
                                             "max_height": request.max_height,
                                             "delete_original": request.delete_original})

            def verify_image(self, result: BatchResult, fmt: str) -> dict[str, Any]:
                item = next(item for item in result.items if item.status == "succeeded")
                artifact = item.artifact
                assert artifact is not None and artifact.publication == "verified"
                assert artifact.path.is_relative_to(root)
                with Image.open(artifact.path) as image:
                    image.load()
                    assert image.format == fmt and image.size == (144, 108)
                actual = digest(artifact.path)
                assert artifact.sha256 == actual
                assert artifact.size_bytes == artifact.path.stat().st_size
                return {"path": artifact.path.relative_to(root).as_posix(), "sha256": actual,
                        "bytes": artifact.size_bytes, "format": fmt, "size": [144, 108]}

            def tick(self) -> None:
                if self.failed or self.done:
                    return
                try:
                    self.step()
                except Exception as exc:
                    trace = exc.__traceback__
                    while trace is not None and trace.tb_next is not None:
                        trace = trace.tb_next
                    receipt["failure_location"] = {"phase": self.phase,
                                                   "type": type(exc).__name__,
                                                   "line": trace.tb_lineno if trace else None}
                    self.fail("CHECK_FAILED")

            def step(self) -> None:
                if self.window is None:
                    self.window = next((window for window in app.topLevelWidgets()
                                        if isinstance(window, MainWindow)), None)
                    if self.window is None:
                        return
                window = self.window
                controller = window.controller
                if controller.busy:
                    return
                if self.phase == "capabilities":
                    capabilities = controller.capabilities
                    assert capabilities is not None
                    receipt["capabilities"] = asdict(capabilities)
                    missing = [fmt for fmt, _ in self.formats
                               if not capabilities.for_format(fmt).encoder_available]
                    receipt["unavailable_selector_disabled"] = {
                        fmt: not bool(window.settings.output_format.model().flags(
                            window.settings.output_format.model().index(index, 0))
                            & Qt.ItemFlag.ItemIsEnabled)
                        for fmt, index in self.formats if fmt in missing
                    }
                    if missing:
                        self.fail("CODEC_PARITY_LOST")
                        return
                    assert capabilities.for_format("AVIF").provider == "Pillow"
                    # Do not activate the fallback merely to inventory its packaged files.
                    assert "pillow_avif" not in sys.modules
                    window.add_paths((source,))
                    self.phase = "selection"
                elif self.phase == "selection":
                    assert controller.paths == (source,)
                    window.settings.resize_check.setChecked(True)
                    window.settings.max_width.setValue(192)
                    window.settings.max_height.setValue(108)
                    window.settings.quality.setValue(80)
                    self.presentation()
                    self.phase = "screens"
                elif self.phase == "screens":
                    self.capture()
                    self.screen += 1
                    if self.screen < 6:
                        self.presentation()
                    else:
                        self.start(self.formats[0][1])
                        self.phase = "codecs"
                elif self.phase == "codecs":
                    result = controller.result
                    assert result is not None and result.status == "succeeded"
                    assert result.counts.succeeded == result.counts.published == 1
                    fmt = self.formats[self.codec][0]
                    artifact = self.verify_image(result, fmt)
                    receipt["cases"].append({"name": fmt, "status": result.status,
                                             "counts": asdict(result.counts), "artifact": artifact})
                    assert digest(source) == initial
                    if fmt == "WEBP":
                        self.prior_webp = artifact["sha256"]
                    self.codec += 1
                    if self.codec < len(self.formats):
                        self.start(self.formats[self.codec][1])
                    else:
                        self.start(1)
                        self.phase = "collision"
                elif self.phase == "collision":
                    result = controller.result
                    assert result is not None and result.status == "failed"
                    assert result.items[0].error is not None
                    assert result.items[0].error.code.value == "OUTPUT_EXISTS"
                    assert result.counts.published == 0
                    assert digest(source.with_suffix(".webp")) == self.prior_webp
                    assert digest(source) == initial
                    receipt["cases"].append({"name": "WEBP-repeat", "status": result.status,
                                             "error": "OUTPUT_EXISTS",
                                             "prior_sha256": self.prior_webp})
                    good, bad = inputs / "partial-good.png", inputs / "partial-bad.png"
                    with Image.new("RGB", (400, 300), (70, 180, 22)) as image:
                        image.save(good)
                    with bad.open("xb") as stream:
                        stream.write(b"synthetic corrupt PNG")
                    for path in (good, bad):
                        sources[path] = digest(path)
                        receipt["sources"].append({"path": path.relative_to(root).as_posix(),
                                                   "sha256": sources[path]})
                    window.clear_button.click()
                    window.add_paths((good, bad))
                    self.phase = "partial-selection"
                elif self.phase == "partial-selection":
                    assert len(controller.paths) == 2
                    self.start(1)
                    self.phase = "partial"
                elif self.phase == "partial":
                    result = controller.result
                    assert result is not None and result.status == "partial"
                    assert result.counts.succeeded == result.counts.failed == 1
                    assert result.counts.published == 1
                    assert result.items[1].error is not None
                    assert result.items[1].error.code.value == "INVALID_IMAGE"
                    assert all(digest(path) == expected for path, expected in sources.items())
                    receipt["cases"].append({"name": "partial", "status": result.status,
                                             "error": "INVALID_IMAGE",
                                             "counts": asdict(result.counts),
                                             "artifact": self.verify_image(result, "WEBP")})
                    assert not any(name.startswith("PyQt") for name in sys.modules)
                    receipt["fallback_imported"] = "pillow_avif" in sys.modules
                    assert not receipt["fallback_imported"]
                    self.queue_delete(True)
                    self.phase = "deletion-true-selection"
                elif self.phase == "deletion-true-selection":
                    assert controller.paths == (self.delete_source,)
                    box = window.settings.delete_original
                    assert box.isEnabled() and not box.isChecked()
                    box.click()  # Real control activation inside the frozen GUI.
                    assert box.isChecked()
                    self.delete_expected = digest(self.delete_source)
                    self.start(1, delete=True)
                    self.phase = "deletion-true"
                elif self.phase == "deletion-true":
                    result = controller.result
                    assert result is not None and result.status == "succeeded"
                    assert result.options is not None and result.options.delete_original
                    assert result.counts.deleted == 1
                    assert result.items[0].source_disposition == "deleted"
                    assert not self.delete_source.exists()
                    receipt["cases"].append({
                        "name": "deletion-true", "status": result.status,
                        "counts": asdict(result.counts),
                        "source_disposition": result.items[0].source_disposition,
                        "source_absent": True, "prior_sha256": self.delete_expected,
                        "artifact": self.verify_image(result, "WEBP"),
                    })
                    self.queue_delete(False)
                    self.phase = "deletion-false-selection"
                elif self.phase == "deletion-false-selection":
                    assert controller.paths == (self.keep_source,)
                    box = window.settings.delete_original
                    assert box.isEnabled() and box.isChecked()
                    box.click()
                    assert not box.isChecked()
                    self.keep_expected = digest(self.keep_source)
                    self.start(1)
                    self.phase = "deletion-false"
                elif self.phase == "deletion-false":
                    result = controller.result
                    assert result is not None and result.status == "succeeded"
                    assert result.options is not None and not result.options.delete_original
                    assert result.counts.deleted == 0
                    assert result.items[0].source_disposition == "retained"
                    assert digest(self.keep_source) == self.keep_expected
                    receipt["cases"].append({
                        "name": "deletion-false", "status": result.status,
                        "counts": asdict(result.counts),
                        "source_disposition": result.items[0].source_disposition,
                        "source_unchanged": True,
                        "artifact": self.verify_image(result, "WEBP"),
                    })
                    self.queue_delete_partial()
                    self.phase = "deletion-partial-selection"
                elif self.phase == "deletion-partial-selection":
                    assert len(controller.paths) == 2
                    box = window.settings.delete_original
                    assert not box.isChecked()
                    box.click()
                    assert box.isChecked()
                    self.partial_bad_expected = digest(self.partial_bad)
                    self.start(1, delete=True)
                    self.phase = "deletion-partial"
                elif self.phase == "deletion-partial":
                    result = controller.result
                    assert result is not None and result.status == "partial"
                    assert result.options is not None and result.options.delete_original
                    assert result.counts.deleted == 1 and result.counts.published == 1
                    dispositions = {item.source.name: item.source_disposition
                                    for item in result.items}
                    assert dispositions[self.partial_good.name] == "deleted"
                    assert dispositions[self.partial_bad.name] == "retained"
                    assert not self.partial_good.exists()
                    assert digest(self.partial_bad) == self.partial_bad_expected
                    receipt["cases"].append({
                        "name": "deletion-partial", "status": result.status,
                        "counts": asdict(result.counts),
                        "dispositions": dispositions,
                        "good_absent": True, "bad_unchanged": True,
                        "artifact": self.verify_image(result, "WEBP"),
                    })
                    receipt["deletion_module_loaded"] = (
                        "image_compressor._windows_deletion" in sys.modules
                    )
                    assert receipt["deletion_module_loaded"]
                    self.done = True
                    timer.stop()
                    window.close()

            def queue_delete(self, delete: bool) -> None:
                assert self.window is not None
                window = self.window
                path = inputs / ("delete-true.png" if delete else "delete-false.png")
                with Image.new("RGB", (400, 300), (27, 143, 201)) as image:
                    image.save(path)
                sources[path] = digest(path)
                if delete:
                    self.delete_source = path
                else:
                    self.keep_source = path
                window.clear_button.click()
                window.add_paths((path,))

            def queue_delete_partial(self) -> None:
                assert self.window is not None
                window = self.window
                self.partial_good = inputs / "delete-partial-good.png"
                self.partial_bad = inputs / "delete-partial-bad.png"
                with Image.new("RGB", (400, 300), (70, 180, 22)) as image:
                    image.save(self.partial_good)
                with self.partial_bad.open("xb") as stream:
                    stream.write(b"synthetic corrupt PNG")
                sources[self.partial_good] = digest(self.partial_good)
                sources[self.partial_bad] = digest(self.partial_bad)
                window.clear_button.click()
                window.add_paths((self.partial_good, self.partial_bad))

        driver = Driver()
        timer = QTimer(app)
        timer.setInterval(150)
        timer.timeout.connect(driver.tick)
        timer.start()
        QTimer.singleShot(60000, lambda: driver.fail("CHECK_TIMEOUT"))
        code = gui_main([sys.executable])  # Actual main/show/exec; exactly one QApplication.
        timer.stop()
        receipt["entry_exit"] = code
        receipt["final_phase"] = driver.phase
        if driver.done and not driver.failed and code == 0:
            assert driver.window is not None and not driver.window.controller.busy
            assert not driver.window.isVisible()
            module_names = ("gui_pyside6_v2.window", "image_compressor.service", "PIL._imaging",
                            "PIL._webp", "PIL._avif", "_pillow_heif", "PySide6.QtCore",
                            "PySide6.QtGui", "PySide6.QtWidgets", "PySide6.QtSvg")
            origins = {}
            for name in module_names:
                module = sys.modules[name]
                assert module.__file__ is not None
                origin = Path(module.__file__).resolve()
                assert origin.is_relative_to(bundle)
                origins[name] = str(origin)
            receipt["modules"] = origins
            receipt["sys_path"] = list(sys.path)
            receipt["loaded_libraries"] = loaded_libraries(bundle)
            receipt["status"], receipt["reason"] = "succeeded", None
        else:
            receipt["reason"] = driver.failure
    except Exception:
        receipt["reason"] = "CHECK_FAILED"
    with (root / "receipt.json").open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return 0 if receipt["status"] == "succeeded" else 1
