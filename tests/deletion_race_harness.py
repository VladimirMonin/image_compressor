"""One bounded, stdlib-only child attempts mutations of its parent's owned fixtures."""

import ctypes
import json
import sys
from pathlib import Path

source, destination = map(Path, sys.argv[1:3])
phase = sys.argv[3]
actions = (
    (("source_write", source, "write"), ("source_rename", source, "rename"),
     ("source_parent_rename", source.parent, "rename"),
     ("destination_parent_rename", destination.parent, "rename"))
    if phase == "source" else
    (("artifact_write", destination, "write"), ("artifact_rename", destination, "rename"))
)
reports = []
for name, path, action in actions:
    try:
        if action == "write":
            dll = ctypes.WinDLL("kernel32", use_last_error=True)
            dll.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32,
                                       ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32,
                                       ctypes.c_void_p]
            dll.CreateFileW.restype = ctypes.c_void_p
            dll.CloseHandle.argtypes = [ctypes.c_void_p]
            dll.CloseHandle.restype = ctypes.c_int
            # Attempt real read/write access without truncation; preserve native Win32 reason.
            raw = dll.CreateFileW(str(path), 0xC0000000, 3, None, 3, 0x00200000, None)
            if raw is None or raw == ctypes.c_void_p(-1).value:
                raise ctypes.WinError(ctypes.get_last_error())
            assert dll.CloseHandle(raw)
        else:
            path.rename(path.with_name(path.name + "-race-renamed"))
    except OSError as exc:
        reports.append({"action": name, "refused": True, "winerror": exc.winerror})
    else:
        reports.append({"action": name, "refused": False})
print(json.dumps(reports))
