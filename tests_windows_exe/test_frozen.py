"""External exact-byte Windows EXE checks. No Qt import, shell launch or source injection.

Collection is inert. Missing explicit artifact is FAIL, never skip. Each launched tree is
assigned to an unnamed kill-on-close Job Object BEFORE its suspended thread is resumed.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from ctypes import wintypes
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]


def digest(path):
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class BasicLimit(ctypes.Structure):
    _fields_ = [("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
                ("flags", wintypes.DWORD), ("minimum_ws", ctypes.c_size_t),
                ("maximum_ws", ctypes.c_size_t), ("active_limit", wintypes.DWORD),
                ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
                ("scheduling", wintypes.DWORD)]


class IOCounts(ctypes.Structure):
    _fields_ = [(name, ctypes.c_ulonglong) for name in
                ("read_ops", "write_ops", "other_ops", "read_bytes", "write_bytes", "other_bytes")]


class ExtendedLimit(ctypes.Structure):
    _fields_ = [("basic", BasicLimit), ("io", IOCounts),
                ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
                ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t)]


class ProcessIds(ctypes.Structure):
    _fields_ = [("assigned", wintypes.DWORD), ("count", wintypes.DWORD),
                ("ids", ctypes.c_size_t * 256)]


class ThreadEntry(ctypes.Structure):
    _fields_ = [("size", wintypes.DWORD), ("usage", wintypes.DWORD),
                ("tid", wintypes.DWORD), ("owner", wintypes.DWORD),
                ("priority", wintypes.LONG), ("delta", wintypes.LONG),
                ("flags", wintypes.DWORD)]


class StartupInfo(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("reserved", wintypes.LPWSTR),
                ("desktop", wintypes.LPWSTR), ("title", wintypes.LPWSTR),
                *[(name, wintypes.DWORD) for name in
                  ("x", "y", "width", "height", "x_chars", "y_chars", "fill", "flags")],
                ("show", wintypes.WORD), ("reserved_size", wintypes.WORD),
                ("reserved_bytes", ctypes.c_void_p), ("stdin", wintypes.HANDLE),
                ("stdout", wintypes.HANDLE), ("stderr", wintypes.HANDLE)]


class MandatoryLabel(ctypes.Structure):
    _fields_ = [("sid", ctypes.c_void_p), ("attributes", wintypes.DWORD)]


class ProcessInfo(ctypes.Structure):
    _fields_ = [("process", wintypes.HANDLE), ("thread", wintypes.HANDLE),
                ("pid", wintypes.DWORD), ("tid", wintypes.DWORD)]


class Native:
    def __init__(self):
        assert sys.platform == "win32", "Frozen qualification requires Windows"
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.user = ctypes.WinDLL("user32", use_last_error=True)
        self.psapi = ctypes.WinDLL("psapi", use_last_error=True)
        self.advapi = ctypes.WinDLL("advapi32", use_last_error=True)
        self.callback_type = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        signatures = (
            (self.kernel, "CreateJobObjectW", [ctypes.c_void_p, wintypes.LPCWSTR], wintypes.HANDLE),
            (self.kernel, "SetInformationJobObject",
             [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            (self.kernel, "QueryInformationJobObject", [wintypes.HANDLE, ctypes.c_int,
                 ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p], wintypes.BOOL),
            (self.kernel, "AssignProcessToJobObject",
             [wintypes.HANDLE, wintypes.HANDLE], wintypes.BOOL),
            (self.kernel, "TerminateJobObject", [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            (self.kernel, "CloseHandle", [wintypes.HANDLE], wintypes.BOOL),
            (self.kernel, "CreateToolhelp32Snapshot",
             [wintypes.DWORD, wintypes.DWORD], wintypes.HANDLE),
            (self.kernel, "Thread32First",
             [wintypes.HANDLE, ctypes.POINTER(ThreadEntry)], wintypes.BOOL),
            (self.kernel, "Thread32Next",
             [wintypes.HANDLE, ctypes.POINTER(ThreadEntry)], wintypes.BOOL),
            (self.kernel, "OpenThread",
             [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            (self.kernel, "ResumeThread", [wintypes.HANDLE], wintypes.DWORD),
            (self.kernel, "OpenProcess",
             [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD], wintypes.HANDLE),
            (self.kernel, "GetCurrentProcess", [], wintypes.HANDLE),
            (self.kernel, "LocalFree", [ctypes.c_void_p], ctypes.c_void_p),
            (self.kernel, "WaitForSingleObject", [wintypes.HANDLE, wintypes.DWORD], wintypes.DWORD),
            (self.kernel, "GetExitCodeProcess",
             [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
            (self.kernel, "TerminateProcess", [wintypes.HANDLE, wintypes.UINT], wintypes.BOOL),
            (self.kernel, "QueryFullProcessImageNameW", [wintypes.HANDLE, wintypes.DWORD,
                 wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
            (self.user, "EnumWindows", [self.callback_type, wintypes.LPARAM], wintypes.BOOL),
            (self.user, "GetWindowThreadProcessId", [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)],
             wintypes.DWORD),
            (self.user, "IsWindowVisible", [wintypes.HWND], wintypes.BOOL),
            (self.user, "GetWindowTextW",
             [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            (self.user, "GetClassNameW",
             [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int], ctypes.c_int),
            (self.user, "PostMessageW", [wintypes.HWND, wintypes.UINT, wintypes.WPARAM,
                                        wintypes.LPARAM], wintypes.BOOL),
            (self.psapi, "EnumProcessModulesEx", [wintypes.HANDLE, ctypes.c_void_p,
                 wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), wintypes.DWORD], wintypes.BOOL),
            (self.psapi, "GetModuleFileNameExW", [wintypes.HANDLE, wintypes.HMODULE,
                                                wintypes.LPWSTR, wintypes.DWORD], wintypes.DWORD),
            (self.advapi, "CreateRestrictedToken",
             [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
              wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD, ctypes.c_void_p,
              ctypes.POINTER(wintypes.HANDLE)], wintypes.BOOL),
            (self.advapi, "SetTokenInformation",
             [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            (self.advapi, "ConvertStringSidToSidW",
             [wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p)], wintypes.BOOL),
            (self.advapi, "GetLengthSid", [ctypes.c_void_p], wintypes.DWORD),
            (self.advapi, "GetSidSubAuthorityCount", [ctypes.c_void_p],
             ctypes.POINTER(ctypes.c_ubyte)),
            (self.advapi, "GetSidSubAuthority", [ctypes.c_void_p, wintypes.DWORD],
             ctypes.POINTER(wintypes.DWORD)),
            (self.advapi, "CreateProcessAsUserW",
             [wintypes.HANDLE, wintypes.LPCWSTR, wintypes.LPWSTR, ctypes.c_void_p,
              ctypes.c_void_p, wintypes.BOOL, wintypes.DWORD, ctypes.c_void_p,
              wintypes.LPCWSTR, ctypes.POINTER(StartupInfo), ctypes.POINTER(ProcessInfo)],
             wintypes.BOOL),
            (self.advapi, "CreateProcessWithTokenW",
             [wintypes.HANDLE, wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPWSTR,
              wintypes.DWORD, ctypes.c_void_p, wintypes.LPCWSTR,
              ctypes.POINTER(StartupInfo), ctypes.POINTER(ProcessInfo)], wintypes.BOOL),
            (self.advapi, "OpenProcessToken", [wintypes.HANDLE, wintypes.DWORD,
                                              ctypes.POINTER(wintypes.HANDLE)], wintypes.BOOL),
            (self.advapi, "GetTokenInformation", [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                 wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)], wintypes.BOOL),
        )
        for library, name, arguments, result in signatures:
            function = getattr(library, name)
            function.argtypes, function.restype = arguments, result

    @staticmethod
    def checked(value):
        if not value:
            raise OSError(ctypes.get_last_error(), "OWNED_WINDOWS_API_FAILED")
        return value

    def elevated(self, process=None):
        token = wintypes.HANDLE()
        process = self.kernel.GetCurrentProcess() if process is None else process
        self.checked(self.advapi.OpenProcessToken(process, 8, ctypes.byref(token)))
        try:
            value, length = wintypes.DWORD(), wintypes.DWORD()
            self.checked(self.advapi.GetTokenInformation(token, 20, ctypes.byref(value),
                                                        ctypes.sizeof(value), ctypes.byref(length)))
            return bool(value.value)
        finally:
            self.kernel.CloseHandle(token)

    def security(self, process):
        token = wintypes.HANDLE()
        self.checked(self.advapi.OpenProcessToken(process, 8, ctypes.byref(token)))
        try:
            length = wintypes.DWORD()
            self.advapi.GetTokenInformation(token, 25, None, 0, ctypes.byref(length))
            assert ctypes.get_last_error() == 122 and length.value > 0
            buffer = ctypes.create_string_buffer(length.value)
            self.checked(self.advapi.GetTokenInformation(token, 25, buffer, len(buffer),
                                                        ctypes.byref(length)))
            label = ctypes.cast(buffer, ctypes.POINTER(MandatoryLabel)).contents
            count = self.advapi.GetSidSubAuthorityCount(label.sid).contents.value
            rid = self.advapi.GetSidSubAuthority(label.sid, count - 1).contents.value
            return {"elevated": self.elevated(process), "integrity_rid": rid}
        finally:
            self.kernel.CloseHandle(token)

    def security_pid(self, pid):
        handle = self.checked(self.kernel.OpenProcess(0x1000, False, pid))
        try:
            return self.security(handle)
        finally:
            self.kernel.CloseHandle(handle)

    def limited_process(self, command, environment, cwd):
        # ONLY the harness's own token, never Explorer/another process/credentials.
        # Prefer its UAC-linked limited token. With no linked token, create a new LUA
        # restricted token, remove privileges, and LOWER its integrity to Medium.
        # No current-token/global security change, privilege enabling or SANDBOX_INERT.
        current, linked = wintypes.HANDLE(), wintypes.HANDLE()
        # QUERY | DUPLICATE | ASSIGN_PRIMARY | ADJUST_DEFAULT on our own token handle;
        # CreateRestrictedToken preserves handle access, needed to lower ONLY the new token.
        self.checked(self.advapi.OpenProcessToken(self.kernel.GetCurrentProcess(), 0x8B,
                                                ctypes.byref(current)))
        try:
            length = wintypes.DWORD()
            policy = "CreateProcessWithTokenW: own linked limited token"
            found = self.advapi.GetTokenInformation(current, 19, ctypes.byref(linked),
                                                   ctypes.sizeof(linked), ctypes.byref(length))
            if not found:
                assert ctypes.get_last_error() == 1312, "Cannot obtain own limited token"
                self.checked(self.advapi.CreateRestrictedToken(
                    current, 0x1 | 0x4, 0, None, 0, None, 0, None, ctypes.byref(linked)))
                sid = ctypes.c_void_p()
                self.checked(self.advapi.ConvertStringSidToSidW("S-1-16-8192", ctypes.byref(sid)))
                try:
                    label = MandatoryLabel(sid, 0x20)  # SE_GROUP_INTEGRITY, Medium RID 8192.
                    size = ctypes.sizeof(label) + self.advapi.GetLengthSid(sid)
                    self.checked(self.advapi.SetTokenInformation(
                        linked, 25, ctypes.byref(label), size))
                finally:
                    self.kernel.LocalFree(sid)
                policy = "CreateProcessAsUserW: own LUA restricted + Medium token"
            elevation = wintypes.DWORD()
            self.checked(self.advapi.GetTokenInformation(
                linked, 20, ctypes.byref(elevation), ctypes.sizeof(elevation),
                ctypes.byref(length)))
            assert not elevation.value, "Refuse to start EXE with an elevated token"
            info, startup = ProcessInfo(), StartupInfo()
            startup.cb = ctypes.sizeof(startup)
            block = ctypes.create_unicode_buffer("\0".join(
                f"{key}={value}" for key, value in sorted(environment.items())) + "\0\0")
            arguments = ctypes.create_unicode_buffer(subprocess.list2cmdline(command))
            if policy.startswith("CreateProcessAsUserW"):
                created = self.advapi.CreateProcessAsUserW(
                    linked, command[0], arguments, None, None, False, 0x4 | 0x400 | 0x200,
                    ctypes.cast(block, ctypes.c_void_p), str(cwd), ctypes.byref(startup),
                    ctypes.byref(info))
            else:
                created = self.advapi.CreateProcessWithTokenW(
                    linked, 0, command[0], arguments, 0x4 | 0x400 | 0x200,
                    ctypes.cast(block, ctypes.c_void_p), str(cwd), ctypes.byref(startup),
                    ctypes.byref(info))
            self.checked(created)
            return NativeProcess(self, info, policy)
        finally:
            if linked:
                self.kernel.CloseHandle(linked)
            self.kernel.CloseHandle(current)

    def elevated_pid(self, pid):
        handle = self.checked(self.kernel.OpenProcess(0x1000, False, pid))
        try:
            return self.elevated(handle)
        finally:
            self.kernel.CloseHandle(handle)

    def new_job(self):
        job = self.checked(self.kernel.CreateJobObjectW(None, None))
        limit = ExtendedLimit()
        limit.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE, this unnamed job only.
        try:
            self.checked(self.kernel.SetInformationJobObject(job, 9, ctypes.byref(limit),
                                                             ctypes.sizeof(limit)))
        except BaseException:
            self.kernel.CloseHandle(job)
            raise
        return job

    def pids(self, job):
        value = ProcessIds()
        self.checked(self.kernel.QueryInformationJobObject(job, 3, ctypes.byref(value),
                                                           ctypes.sizeof(value), None))
        assert value.count <= 256, "Owned Job Object PID inventory overflow"
        return {int(pid) for pid in value.ids[:value.count]}

    def resume_owned(self, pid):
        snapshot = self.kernel.CreateToolhelp32Snapshot(4, 0)  # TH32CS_SNAPTHREAD
        assert snapshot not in (None, ctypes.c_void_p(-1).value)
        try:
            item = ThreadEntry()
            item.size = ctypes.sizeof(item)
            present = self.kernel.Thread32First(snapshot, ctypes.byref(item))
            while present:
                if item.owner == pid:
                    thread = self.checked(self.kernel.OpenThread(2, False, item.tid))
                    try:
                        assert self.kernel.ResumeThread(thread) == 1
                        return
                    finally:
                        self.kernel.CloseHandle(thread)
                present = self.kernel.Thread32Next(snapshot, ctypes.byref(item))
            raise AssertionError("Owned suspended process thread not found")
        finally:
            self.kernel.CloseHandle(snapshot)

    def image(self, pid):
        handle = self.checked(self.kernel.OpenProcess(0x1000, False, pid))
        try:
            buffer = ctypes.create_unicode_buffer(32768)
            length = wintypes.DWORD(len(buffer))
            self.checked(self.kernel.QueryFullProcessImageNameW(handle, 0, buffer,
                                                               ctypes.byref(length)))
            return str(Path(buffer.value).resolve())
        finally:
            self.kernel.CloseHandle(handle)

    def windows(self, owned):
        result = []

        @self.callback_type
        def callback(hwnd, _):
            pid = wintypes.DWORD()
            self.user.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            # Do not read title/class/content from another worker's window.
            if pid.value in owned and self.user.IsWindowVisible(hwnd):
                title, name = ctypes.create_unicode_buffer(512), ctypes.create_unicode_buffer(128)
                self.user.GetWindowTextW(hwnd, title, len(title))
                self.user.GetClassNameW(hwnd, name, len(name))
                result.append({"hwnd": int(hwnd), "pid": pid.value,
                               "title": title.value, "class": name.value})
            return True

        self.checked(self.user.EnumWindows(callback, 0))
        return result

    def modules(self, pid):
        handle = self.checked(self.kernel.OpenProcess(0x410, False, pid))
        try:
            modules = (wintypes.HMODULE * 2048)()
            size = wintypes.DWORD()
            self.checked(self.psapi.EnumProcessModulesEx(handle, modules, ctypes.sizeof(modules),
                                                         ctypes.byref(size), 3))
            assert size.value <= ctypes.sizeof(modules)
            result = []
            for module in modules[:size.value // ctypes.sizeof(wintypes.HMODULE)]:
                buffer = ctypes.create_unicode_buffer(32768)
                self.checked(self.psapi.GetModuleFileNameExW(handle, module, buffer, len(buffer)))
                result.append(str(Path(buffer.value).resolve()))
            return result
        finally:
            self.kernel.CloseHandle(handle)


class NativeProcess:
    """Small owned-handle equivalent of Popen for an explicitly limited-token launch."""
    def __init__(self, native, info, policy):
        self.native, self.pid, self.policy = native, info.pid, policy
        self._handle, self._thread = info.process, info.thread
        self.returncode = None

    def resume(self):
        assert self.native.kernel.ResumeThread(self._thread) == 1
        self.native.kernel.CloseHandle(self._thread)
        self._thread = None

    def poll(self):
        state = self.native.kernel.WaitForSingleObject(self._handle, 0)
        if state == 0x102:
            return None
        assert state == 0
        value = wintypes.DWORD()
        self.native.checked(self.native.kernel.GetExitCodeProcess(
            self._handle, ctypes.byref(value)))
        self.returncode = value.value
        return self.returncode

    def wait(self, timeout):
        state = self.native.kernel.WaitForSingleObject(self._handle, int(timeout * 1000))
        if state == 0x102:
            raise subprocess.TimeoutExpired("owned limited-token EXE", timeout)
        assert state == 0
        return self.poll()

    def terminate(self):
        self.native.checked(self.native.kernel.TerminateProcess(self._handle, 124))

    def close(self):
        if self._thread:
            self.native.kernel.CloseHandle(self._thread)
        self.native.kernel.CloseHandle(self._handle)


@pytest.fixture(scope="session")
def artifact():
    raw = os.environ.get("IC_FROZEN_EXE")
    if not raw or not Path(raw).is_absolute() or not Path(raw).is_file():
        pytest.fail("IC_FROZEN_EXE must explicitly name an existing absolute candidate EXE")
    path = Path(raw).resolve(strict=True)
    assert path.name == "ImageCompressorV2.exe"
    info = json.loads((path.parent / "BUILD-INFO.json").read_text(encoding="utf-8"))
    assert info["mode"] == "onefile", "This finite runner qualifies the planned one-file artifact"
    assert info["sha256"] == digest(path) and info["bytes"] == path.stat().st_size
    with path.open("rb") as stream:
        assert stream.read(2) == b"MZ"
        stream.seek(0x3C)
        pe_offset = struct.unpack("<I", stream.read(4))[0]
        stream.seek(pe_offset)
        assert stream.read(4) == b"PE\0\0"
        assert struct.unpack("<H", stream.read(2))[0] == 0x8664  # AMD64, not ARM/Win32.
        stream.seek(pe_offset + 24)
        assert struct.unpack("<H", stream.read(2))[0] == 0x20B  # PE32+.
        stream.seek(pe_offset + 24 + 68)
        assert struct.unpack("<H", stream.read(2))[0] == 2  # Windowed GUI subsystem.
    return path, info


class OwnedRun:
    def __init__(self, artifact_value, root):
        self.source, self.info = artifact_value
        self.root = root
        self.native = Native()
        self.launcher_elevated = self.native.elevated()
        self.root.mkdir()
        self.portable = root / "только EXE Ә пробел"
        self.portable.mkdir()
        self.exe = self.portable / "ImageCompressorV2.exe"
        shutil.copyfile(self.source, self.exe)
        assert digest(self.exe) == self.info["sha256"]
        self.cwd, self.temp = root / "empty cwd", root / "temporary"
        self.cwd.mkdir()
        self.temp.mkdir()
        profile = root / "isolated profile"
        profile.mkdir()
        for name in ("Local", "Roaming"):
            (profile / name).mkdir()
        windows = Path(os.environ["SYSTEMROOT"]).resolve()
        self.environment = {name: os.environ[name] for name in
                            ("SYSTEMROOT", "WINDIR", "SYSTEMDRIVE", "COMSPEC", "PATHEXT")
                            if name in os.environ}
        self.environment.update(
            PATH=os.pathsep.join((str(windows / "System32"), str(windows))),
            TEMP=str(self.temp), TMP=str(self.temp), TMPDIR=str(self.temp),
            USERPROFILE=str(profile), LOCALAPPDATA=str(profile / "Local"),
            APPDATA=str(profile / "Roaming"),
        )
        self.job = self.native.new_job()
        self.process = None
        self.stdout = self.stderr = None
        self.observed = set()
        self.evidence = {"sha256": self.info["sha256"], "cwd": str(self.cwd),
                         "environment_policy": "Windows PATH; fresh temp/profile; no Python/Qt",
                         "environment_keys": sorted(self.environment),
                         "launcher_parent_elevated": self.launcher_elevated,
                         "forced_cleanup": False, "timed_out": False}

    def __enter__(self):
        return self

    def launch(self, arguments):
        self.stdout = (self.root / "stdout.txt").open("xb")
        self.stderr = (self.root / "stderr.txt").open("xb")
        command = [str(self.exe), *map(str, arguments)]
        self.evidence.update(argv=command, started=time.time())
        if self.launcher_elevated:
            self.process = self.native.limited_process(command, self.environment, self.cwd)
            self.evidence["launch_method"] = self.process.policy
            self.evidence["stdio_policy"] = "windowed null stdio; receipt + native exit evidence"
        else:
            self.process = subprocess.Popen(
                command, cwd=self.cwd, env=self.environment, stdout=self.stdout, stderr=self.stderr,
                creationflags=0x4 | subprocess.CREATE_NEW_PROCESS_GROUP,  # CREATE_SUSPENDED
            )
            self.evidence["launch_method"] = "non-elevated Popen"
        try:
            self.native.checked(self.native.kernel.AssignProcessToJobObject(
                self.job, int(self.process._handle)))
            security = self.native.security(self.process._handle)
            self.evidence["application_security"] = security
            assert not security["elevated"], "Actual EXE must not run elevated"
            assert security["integrity_rid"] == 8192, "Actual EXE must have Medium integrity"
            self.observed.add(self.process.pid)
            if isinstance(self.process, NativeProcess):
                self.process.resume()
            else:
                self.native.resume_owned(self.process.pid)
        except BaseException:
            self.process.terminate()  # Only this still-owned, suspended process.
            self.process.wait(timeout=5)
            raise
        self.evidence["bootloader_pid"] = self.process.pid

    def observe(self):
        active = self.native.pids(self.job)
        self.observed.update(active)
        windows = self.native.windows(active)
        for window in windows:
            if window["title"].startswith("Image Compressor") and window["class"].startswith("Qt"):
                if "visible_window" not in self.evidence:
                    window["image"] = self.native.image(window["pid"])
                    window["security"] = self.native.security_pid(window["pid"])
                    assert not window["security"]["elevated"], "Qt child must not run elevated"
                    assert window["security"]["integrity_rid"] == 8192
                    assert Path(window["image"]) == self.exe
                    self.evidence["visible_window"] = window
                return window
        return None

    def wait(self, seconds):
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self.observe()
            if self.process.poll() is not None and not self.native.pids(self.job):
                self.evidence["raw_exit"] = self.process.returncode
                self.evidence["normal_tree_exit"] = True
                assert not list(self.temp.glob("_MEI*")), "One-file extraction leaked after exit"
                assert list(self.cwd.iterdir()) == []
                assert list(self.portable.iterdir()) == [self.exe]
                return self.process.returncode
            time.sleep(0.04)
        self.evidence["timed_out"] = True
        raise AssertionError("OWNED_EXE_TIMEOUT: cleanup is failure, never a passing close")

    def __exit__(self, kind, value, traceback):
        try:
            active = self.native.pids(self.job)
            self.evidence["active_before_cleanup"] = sorted(active)
            self.evidence["raw_exit_before_cleanup"] = (
                self.process.poll() if self.process is not None else None)
            if active:
                self.evidence["forced_cleanup"] = True
                self.native.checked(self.native.kernel.TerminateJobObject(self.job, 124))
                if self.process is not None:
                    self.process.wait(timeout=5)
                deadline = time.monotonic() + 5
                while self.native.pids(self.job) and time.monotonic() < deadline:
                    time.sleep(0.02)
            self.evidence["remaining_pids"] = sorted(self.native.pids(self.job))
            self.evidence["extractions_after_exit"] = [str(p) for p in self.temp.glob("_MEI*")]
            self.evidence["observed_pids"] = sorted(self.observed)
            self.evidence["outcome"] = (
                "succeeded" if kind is None and not self.evidence["forced_cleanup"] else "failed")
        finally:
            self.native.kernel.CloseHandle(self.job)
            if isinstance(self.process, NativeProcess):
                self.process.close()
            for stream in (self.stdout, self.stderr):
                if stream is not None:
                    stream.close()
            (self.root / "external.json").write_text(
                json.dumps(self.evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if kind is None:
            assert not self.evidence["forced_cleanup"] and not self.evidence["remaining_pids"]
        return False


@pytest.mark.timeout(42)
def test_no_argument_visible_launch(artifact, tmp_path):
    with OwnedRun(artifact, tmp_path / "cold native") as run:
        run.launch([])
        deadline = time.monotonic() + 25
        window = None
        while time.monotonic() < deadline and run.process.poll() is None:
            window = run.observe()
            if window:
                break
            time.sleep(0.05)
        assert window is not None, "The actual new native window never became visible"
        assert window["pid"] != run.process.pid, "One-file child ownership was not observed"
        extracted = list(run.temp.glob("_MEI*"))
        assert len(extracted) == 1
        modules = run.native.modules(window["pid"])
        assert any(Path(path).name.lower() == "qwindows.dll" for path in modules)
        assert any(Path(path).name.lower() == "python314.dll" for path in modules)
        windows = Path(os.environ["SYSTEMROOT"]).resolve()
        for raw in modules:
            path = Path(raw)
            assert (path == run.exe or path.is_relative_to(extracted[0])
                    or path.is_relative_to(windows))
            if path.is_relative_to(extracted[0]):
                key = path.relative_to(extracted[0]).as_posix().lower()
                expected = {key.replace("\\", "/").lower(): value
                            for key, value in run.info["payload_sha256"].items()}
                assert digest(path) == expected[key]
        run.evidence["native_modules"] = modules
        run.native.checked(run.native.user.PostMessageW(window["hwnd"], 0x10, 0, 0))  # WM_CLOSE
        assert run.wait(12) == 0
        assert "visible_window" in run.evidence and len(run.observed) >= 2


@pytest.mark.timeout(72)
def test_real_frozen_gui_codecs_resources_and_teardown(artifact, tmp_path):
    with OwnedRun(artifact, tmp_path / "cold qualification") as run:
        output = run.root / "actual synthetic qualification"
        run.launch(["--packaging-check", str(output)])
        code = run.wait(65)
        receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
        assert code == 0, receipt
        assert receipt["status"] == "succeeded" and receipt["reason"] is None
        assert receipt["entry_exit"] == 0 and receipt["frozen"]
        assert receipt["exe_sha256"] == run.info["sha256"]
        assert Path(receipt["executable"]) == run.exe
        assert receipt["parent_pid"] == run.process.pid
        assert receipt["pid"] in run.observed and receipt["pid"] != run.process.pid
        assert run.evidence["visible_window"]["pid"] == receipt["pid"]
        assert receipt["platform"] == "windows" and not receipt["fallback_imported"]
        bundle = Path(receipt["bundle"])
        assert bundle.is_relative_to(run.temp) and not bundle.exists()
        assert all(Path(path).is_relative_to(bundle) for path in receipt["modules"].values())
        assert not any("pyqt" in name.lower() for name in receipt["modules"])
        assert all(Path(path).is_relative_to(bundle) for path in receipt["sys_path"])
        expected_payload = {key.replace("\\", "/").lower(): value
                            for key, value in run.info["payload_sha256"].items()}
        for module in receipt["loaded_libraries"]:
            path = Path(module["path"])
            if module["origin"] == "bundle":
                assert path.is_relative_to(bundle)
                key = path.relative_to(bundle).as_posix().lower()
                assert module["sha256"] == expected_payload[key]
            elif module["origin"] == "self":
                assert path == run.exe and module["sha256"] == run.info["sha256"]
            else:
                assert module["origin"] == "windows"
                assert path.is_relative_to(Path(os.environ["SYSTEMROOT"]).resolve())
        for name, data in receipt["resources"].items():
            key = "gui_pyside6_v2/" + name
            assert data["sha256"] == run.info["inputs"][key]
            assert Path(data["path"]).is_relative_to(bundle)
        expected_assets = sorted(
            path.relative_to(REPO / "gui_pyside6_v2").as_posix()
            for path in (REPO / "gui_pyside6_v2/assets").glob("*.svg")
        )
        assert len(expected_assets) == 13
        assert sorted(receipt["resources"]) == sorted(["tokens.json", *expected_assets])
        for name in expected_assets:
            repo_asset = (REPO / "gui_pyside6_v2" / name).read_bytes()
            # Same git blob may be checked out as LF or CRLF; the frozen build snapshots
            # the staged (autocrlf) representation, so accept both byte representations.
            expected = {
                hashlib.sha256(repo_asset).hexdigest(),
                hashlib.sha256(repo_asset.replace(b"\r\n", b"\n").replace(
                    b"\n", b"\r\n")).hexdigest(),
            }
            assert receipt["resources"][name]["sha256"] in expected, name
        assert receipt["forbidden_modules_absent"] is True
        assert not any(name in receipt["modules"] for name in ("gui", "classes", "gui_main"))
        assert receipt["deletion_module_loaded"] is True
        assert receipt["deletion_available"] is True
        caps = {item["format"]: item for item in receipt["capabilities"]["formats"]}
        for fmt in ("JPEG", "WEBP", "HEIF", "AVIF"):
            assert caps[fmt]["encoder_available"] and caps[fmt]["roundtrip_verified"]
            assert caps[fmt]["reason"] is None
        assert caps["AVIF"]["provider"] == "Pillow" and caps["HEIF"]["provider"] == "pillow_heif"
        assert receipt["start_actions"] == len(receipt["requests"]) == 9
        assert [item["output_format"] for item in receipt["requests"]] == [
            "WEBP", "JPEG", "HEIF", "AVIF", "WEBP", "WEBP", "WEBP", "WEBP", "WEBP"]
        assert all(item["quality"] == 80 and item["max_width"] == 192
                   and item["max_height"] == 108 for item in receipt["requests"])
        assert [item["delete_original"] for item in receipt["requests"]] == [
            False, False, False, False, False, False, True, False, True]
        cases = receipt["cases"]
        assert [item["name"] for item in cases] == [
            "WEBP", "JPEG", "HEIF", "AVIF", "WEBP-repeat", "partial",
            "deletion-true", "deletion-false", "deletion-partial"]
        assert cases[4]["error"] == "OUTPUT_EXISTS" and cases[4]["status"] == "failed"
        assert cases[4]["prior_sha256"] == cases[0]["artifact"]["sha256"]
        assert cases[5]["status"] == "partial" and cases[5]["error"] == "INVALID_IMAGE"
        assert cases[5]["counts"]["succeeded"] == cases[5]["counts"]["failed"] == 1
        assert cases[5]["counts"]["published"] == 1
        assert cases[6]["status"] == "succeeded" and cases[6]["counts"]["deleted"] == 1
        assert cases[6]["source_disposition"] == "deleted" and cases[6]["source_absent"]
        assert cases[7]["status"] == "succeeded" and cases[7]["counts"]["deleted"] == 0
        assert cases[7]["source_disposition"] == "retained" and cases[7]["source_unchanged"]
        assert cases[8]["status"] == "partial" and cases[8]["counts"]["deleted"] == 1
        assert cases[8]["good_absent"] and cases[8]["bad_unchanged"]
        assert cases[8]["dispositions"]["delete-partial-good.png"] == "deleted"
        assert cases[8]["dispositions"]["delete-partial-bad.png"] == "retained"

        # Independent decoder process context; these packages are NOT on EXE's lookup path.
        import pillow_heif
        from PIL import Image

        pillow_heif.register_heif_opener()
        for case in [*cases[:4], cases[5], cases[6], cases[7], cases[8]]:
            item = case["artifact"]
            path = output / item["path"]
            assert path.resolve().is_relative_to(output)
            assert digest(path) == item["sha256"] and path.stat().st_size == item["bytes"]
            with Image.open(path) as image:
                image.load()
                assert image.format == item["format"] and image.size == (144, 108)
        for source in receipt["sources"]:
            path = output / source["path"]
            assert digest(path) == source["sha256"]
            if "partial-bad" in path.name:
                assert path.read_bytes() == b"synthetic corrupt PNG"
            else:
                with Image.open(path) as image:
                    image.load()
                    assert image.format == "PNG" and image.size == (400, 300)
        screens = receipt["screens"]
        assert len(screens) == len({item["sha256"] for item in screens}) == 6
        assert {(item["locale"].lower(), item["theme"]) for item in screens} == {
            (language, theme) for language in ("ru", "en", "kk") for theme in ("light", "dark")}
        assert any(item["logical_size"] == [900, 640] for item in screens)
        for screen in screens:
            path = output / screen["path"]
            assert digest(path) == screen["sha256"]
            assert screen["resolved_font"] == "Segoe UI" and screen["svg_visible"]
            with Image.open(path) as image:
                assert list(image.size) == screen["png_size"]


@pytest.mark.timeout(20)
def test_frozen_argument_refusals_do_not_mutate_prior_root(artifact, tmp_path):
    for index, arguments in enumerate((("--unknown",), ("--packaging-check", "relative"), ())):
        with OwnedRun(artifact, tmp_path / f"refusal-{index}") as run:
            if index == 2:
                prior = run.root / "occupied"
                prior.mkdir()
                sentinel = prior / "sentinel"
                sentinel.write_bytes(b"preserve this exact prior evidence")
                arguments = ("--packaging-check", str(prior))
            run.launch(arguments)
            assert run.wait(5) == 2
            assert "visible_window" not in run.evidence
            if index == 2:
                assert list(prior.iterdir()) == [sentinel]
                assert sentinel.read_bytes() == b"preserve this exact prior evidence"
