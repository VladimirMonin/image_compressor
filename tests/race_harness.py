"""Two real processes rendezvous immediately before the actual os.link boundary."""

import json
import sys
import time
from pathlib import Path

# Source-tree harness only. Installed smoke tests explicitly do not do this.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from image_compressor import ConversionRequest, convert  # noqa: E402
from image_compressor import filesystem as fs  # noqa: E402

source, root = Path(sys.argv[1]), Path(sys.argv[2])
original = fs.publish_new


def publish(staging, destination):
    (root / f"ready-{sys.argv[3]}").touch()
    deadline = time.monotonic() + 25
    while not (root / "go").exists():
        if time.monotonic() >= deadline:
            raise TimeoutError
        time.sleep(0.01)
    original(staging, destination)


fs.publish_new = publish
result = convert(ConversionRequest([source]))
print(
    json.dumps(
        {
            "status": result.status,
            "code": result.items[0].error.code if result.items[0].error else None,
        }
    )
)
