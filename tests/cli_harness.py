"""Fault/signal synchronization seams only; real cli.main, service, codec and filesystem."""

import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from image_compressor import cli, imaging  # noqa: E402

mode = sys.argv[1]
original = imaging.encode
previous = signal.getsignal(signal.SIGINT)


def encode(*args, **kwargs):
    prepared = original(*args, **kwargs)
    if mode == "signal":
        signal.raise_signal(signal.SIGINT)
    elif mode == "internal":
        raise RuntimeError("PRIVATE_EXCEPTION_SENTINEL")
    return prepared


class BrokenOutput:
    def write(self, text):
        raise BrokenPipeError("PRIVATE_DELIVERY_SENTINEL")

    def flush(self):
        raise BrokenPipeError("PRIVATE_DELIVERY_SENTINEL")

    def close(self):
        pass


imaging.encode = encode
if mode == "delivery":
    sys.stdout = BrokenOutput()
exit_code = cli.main(sys.argv[2:])
assert signal.getsignal(signal.SIGINT) == previous
if mode == "delivery":
    sys.stdout = sys.__stdout__
raise SystemExit(exit_code)
