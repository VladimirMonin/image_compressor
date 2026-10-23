"""Thin frozen launcher; no-argument startup is the unchanged public GUI main."""
from __future__ import annotations

import sys
from collections.abc import Sequence


def main(arguments: Sequence[str] | None = None) -> int:
    args = tuple(sys.argv[1:] if arguments is None else arguments)
    if args and (len(args) != 2 or args[0] != "--packaging-check"):
        return 2
    try:
        if args:
            # Opt-in only. Normal double-click does not import the qualification driver.
            from ic_frozen_check import run

            return run(args[1])
        from gui_pyside6_v2.__main__ import main as gui_main

        return gui_main([sys.executable])
    except Exception:
        if not args and sys.platform == "win32":
            import ctypes

            ctypes.windll.user32.MessageBoxW(
                None, "The application could not start. Check the supplied build instructions.",
                "Image Compressor", 0x10,
            )
        # Windowed stdout/stderr may be None; never print/flush raw exceptions.
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
