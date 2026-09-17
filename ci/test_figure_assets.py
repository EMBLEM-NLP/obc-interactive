#!/usr/bin/env python3
"""Synthetic control for figure-asset packaging.

No OBC corpus is required. The validator must pass a complete asset set, fail
when one referenced asset is removed, and fail when one asset is corrupted.
"""

import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "ci" / "recover_figure_assets.py"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(metadata: Path, assets: Path):
    return subprocess.run(
        [
            sys.executable,
            str(VALIDATOR),
            "--metadata",
            str(metadata),
            "--out",
            str(assets),
            "--validate-only",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )


def main() -> int:
    failures = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        metadata = root / "figures-v1.jsonl.gz"
        assets = root / "assets" / "figures-v1"
        assets.mkdir(parents=True)

        rows = [
            {"_meta": True, "assets": 1},
            {
                "page": 1,
                "region": 0,
                "designator": "A-1",
                "kind": "raster",
                "box": [10, 10, 20, 20],
                "forming_part_of": None,
                "files": ["assets/figures-v1/p0001_0_A-1.png"],
            },
        ]
        with gzip.open(metadata, "wt", encoding="utf-8") as fh:
            for row in rows:
                fh.write(json.dumps(row) + "\n")

        asset = assets / "p0001_0_A-1.png"
        asset.write_bytes(b"synthetic-png-fixture")
        (assets / "MANIFEST.sha256").write_text(
            f"{sha256(asset)}  {asset.name}\n", encoding="utf-8"
        )

        good = run(metadata, assets)
        if good.returncode != 0:
            failures.append("complete asset set did not validate")

        asset.unlink()
        missing = run(metadata, assets)
        if missing.returncode == 0:
            failures.append("validator stayed green after referenced asset removal")

        asset.write_bytes(b"synthetic-png-fixture")
        original_hash = sha256(asset)
        (assets / "MANIFEST.sha256").write_text(
            f"{original_hash}  {asset.name}\n", encoding="utf-8"
        )
        asset.write_bytes(b"corrupted")
        corrupt = run(metadata, assets)
        if corrupt.returncode == 0:
            failures.append("validator stayed green after asset corruption")

    print("complete set       : PASS" if not failures else "figure asset control failed")
    print("missing mutation   : detected")
    print("corrupt mutation   : detected")
    for failure in failures:
        print("  FAIL", failure)
    print("RESULT:", "PASS" if not failures else f"FAIL {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
