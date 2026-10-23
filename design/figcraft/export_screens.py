"""Export the saved native through the official FigCraft CLI into a fresh run root."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

FRAMES = [
    ("RU-Light-Empty", 43),
    ("RU-Light-Queue", 115),
    ("RU-Light-Processing", 206),
    ("RU-Dark-Empty", 298),
    ("RU-Dark-Queue", 370),
    ("RU-Dark-Processing", 461),
    ("EN-Light-Queue", 553),
    ("KK-Dark-Queue", 644),
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cli", required=True, type=Path)
    parser.add_argument("--run", required=True)
    parser.add_argument("--evidence", type=Path)
    args = parser.parse_args()
    design = Path(__file__).resolve().parents[1]
    if not args.run or Path(args.run).name != args.run:
        parser.error("--run must be a single new directory name")
    destination = design / "exports" / args.run
    destination.mkdir(exist_ok=False)
    evidence = args.evidence.resolve() if args.evidence else None
    if evidence:
        evidence.relative_to(design.parent)
        evidence.mkdir(parents=True, exist_ok=False)
    native = design / "figcraft/image-compressor-v2.figcraft"
    manifest = {
        "renderer": "FigCraft 0.10.0 official CLI / system fonts",
        "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
        "screens": [],
    }
    for name, ident in FRAMES:
        theme = name.split("-")[1].lower()
        folder = destination / theme
        folder.mkdir(exist_ok=True)
        output = folder / (name + ".png")
        argv = [
            str(args.cli),
            "export",
            str(native),
            "--node",
            str(ident),
            "--format",
            "png",
            "--scale",
            "1",
            "-o",
            str(output),
            "--automation-read-root",
            str(design),
            "--automation-write-root",
            str(destination),
        ]
        result = subprocess.run(argv, capture_output=True, timeout=60)
        if evidence:
            (evidence / (name + ".command.json")).write_text(
                json.dumps({"argv": argv, "exit": result.returncode}, indent=2), encoding="utf-8"
            )
            (evidence / (name + ".stdout.txt")).write_bytes(result.stdout)
            (evidence / (name + ".stderr.txt")).write_bytes(result.stderr)
        if result.returncode:
            raise SystemExit(result.returncode)
        manifest["screens"].append(
            {
                "frame": name,
                "id": ident,
                "file": output.relative_to(design).as_posix(),
                "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            }
        )
    icon = design / "exports" / args.run / "Icon-Add.svg"
    result = subprocess.run(
        [
            str(args.cli),
            "export",
            str(native),
            "--node",
            "40",
            "--format",
            "svg",
            "-o",
            str(icon),
            "--automation-read-root",
            str(design),
            "--automation-write-root",
            str(destination),
        ],
        capture_output=True,
        timeout=60,
    )
    if evidence:
        (evidence / "icon-exit.txt").write_text(str(result.returncode), encoding="utf-8")
    if result.returncode:
        raise SystemExit(result.returncode)
    (destination / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
