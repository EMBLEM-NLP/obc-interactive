#!/usr/bin/env python3
"""No-data regression tests for ci/install_release.py."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import zipfile

PKG = Path(__file__).resolve().parents[1]
INSTALLER = PKG / "ci" / "install_release.py"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INSTALLER), *args],
        cwd=PKG,
        text=True,
        capture_output=True,
    )


def manifest_for(a: bytes, b: bytes) -> dict:
    return {
        "schema_version": 1,
        "release": "synthetic-test",
        "edition": "test",
        "current_through": "2026-01-01",
        "artifact_base_url": "https://invalid.example.test/release",
        "artifacts": [
            {
                "asset": "a.bin",
                "install_path": "emitters/a.bin",
                "bytes": len(a),
                "sha256": digest(a),
            },
            {
                "asset": "b.bin",
                "install_path": "model/b.bin",
                "bytes": len(b),
                "sha256": digest(b),
            },
        ],
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="obc-release-test-") as tmp:
        root = Path(tmp)
        a = b"alpha\n"
        b = b"beta\n"
        manifest = manifest_for(a, b)
        manifest_path = root / "manifest.json"
        manifest_path.write_text(json.dumps(manifest))
        archive = root / "release.zip"
        with zipfile.ZipFile(archive, "w") as package:
            package.writestr("a.bin", a)
            package.writestr("b.bin", b)

        target = root / "installed"
        result = run(
            "--manifest", str(manifest_path),
            "--archive", str(archive),
            "--root", str(target),
        )
        assert result.returncode == 0, result.stderr + result.stdout
        assert (target / "emitters" / "a.bin").read_bytes() == a
        assert (target / "model" / "b.bin").read_bytes() == b
        stamp = json.loads((target / ".obc-release.json").read_text())
        assert stamp["release"] == "synthetic-test"

        # Idempotent re-run should stay green without mutating content.
        second = run(
            "--manifest", str(manifest_path),
            "--archive", str(archive),
            "--root", str(target),
        )
        assert second.returncode == 0, second.stderr + second.stdout
        assert "2 already correct; 0 need installation" in second.stdout

        check = run(
            "--manifest", str(manifest_path),
            "--root", str(target),
            "--check-only",
        )
        assert check.returncode == 0, check.stderr + check.stdout

        # A bad archive must fail before installing any of its staged files.
        bad_root = root / "bad-installed"
        bad_archive = root / "bad.zip"
        with zipfile.ZipFile(bad_archive, "w") as package:
            package.writestr("a.bin", a)
            package.writestr("b.bin", b"CORRUPT")
        bad = run(
            "--manifest", str(manifest_path),
            "--archive", str(bad_archive),
            "--root", str(bad_root),
        )
        assert bad.returncode != 0
        assert not (bad_root / "emitters" / "a.bin").exists()
        assert not (bad_root / "model" / "b.bin").exists()

        # Unsafe install paths are rejected before extraction/install.
        unsafe = manifest_for(a, b)
        unsafe["artifacts"][0]["install_path"] = "../escape.bin"
        unsafe_path = root / "unsafe.json"
        unsafe_path.write_text(json.dumps(unsafe))
        traversal = run(
            "--manifest", str(unsafe_path),
            "--archive", str(archive),
            "--root", str(root / "unsafe-root"),
        )
        assert traversal.returncode != 0
        assert not (root / "escape.bin").exists()

    print("RESULT: PASS — release installer verifies, is idempotent, and fails closed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
