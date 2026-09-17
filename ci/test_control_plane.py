#!/usr/bin/env python3
"""Regression test for ci/run_gates.py --control-plane.

Proves four properties without any OBC corpus data:
1. a missing derived corpus does not make control-plane mode red;
2. a failing no_data gate still makes control-plane mode red;
3. data-dependent checks are never executed in control-plane mode;
4. the ordinary full board still fails closed at DATA1 when data is absent.
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "ci" / "run_gates.py"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run(pkg, manifest, out, *extra):
    return subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--pkg",
            str(pkg),
            "--manifest",
            str(manifest),
            "--out",
            str(out),
            *extra,
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )


def main():
    failures = []
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        pkg = root / "pkg"
        manifest = root / "checks.yaml"
        board = root / "board.json"
        marker = root / "data-ran"

        pass_check = pkg / "checks" / "pass.py"
        data_check = pkg / "checks" / "data_should_not_run.py"
        integrity = pkg / "harden" / "checks" / "check40_dataintegrity.py"

        write(pass_check, 'print("RESULT: PASS")\n')
        write(
            data_check,
            "from pathlib import Path\n"
            f"Path({str(marker)!r}).write_text('ran')\n"
            'print("RESULT: FAIL - data check executed")\n'
            "raise SystemExit(1)\n",
        )
        write(
            integrity,
            'print("RESULT: FAIL - synthetic corpus missing")\n'
            "raise SystemExit(1)\n",
        )

        spec = {
            "epoch_env": {
                "PYTHONHASHSEED": "0",
                "SOURCE_DATE_EPOCH": "1737072000",
                "TZ": "UTC",
            },
            "checks": [
                {
                    "script": "checks/pass.py",
                    "scope": ".",
                    "gate": "CP1",
                    "no_data": True,
                },
                {
                    "script": "checks/data_should_not_run.py",
                    "scope": ".",
                    "gate": "DX",
                },
                {
                    "script": "harden/checks/check40_dataintegrity.py",
                    "scope": "harden",
                    "gate": "DATA1",
                },
            ],
        }
        manifest.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")

        r = run(pkg, manifest, board, "--control-plane")
        b = json.loads(board.read_text())
        if r.returncode != 0:
            failures.append(f"control-plane unexpectedly failed: {r.stdout[-400:]}")
        if b["summary"].get("mode") != "control-plane":
            failures.append("control-plane board does not identify summary.mode")
        if b["summary"].get("data_available") is not False:
            failures.append("control-plane board does not record data_available=false")
        if marker.exists():
            failures.append("a data-dependent check executed in control-plane mode")
        statuses = {row["gate"]: row["status"] for row in b["gates"]}
        if statuses.get("CP1") != "PASS":
            failures.append(f"CP1 was not PASS: {statuses.get('CP1')}")
        if statuses.get("DX") != "SKIP" or statuses.get("DATA1") != "SKIP":
            failures.append(f"data gates were not explicit SKIPs: {statuses}")

        write(
            pass_check,
            'print("RESULT: FAIL - synthetic control-plane failure")\n'
            "raise SystemExit(1)\n",
        )
        marker.unlink(missing_ok=True)
        r = run(pkg, manifest, board, "--control-plane")
        if r.returncode == 0:
            failures.append("control-plane stayed green on a failing no_data gate")
        if marker.exists():
            failures.append("a data-dependent check executed while control plane was red")

        write(pass_check, 'print("RESULT: PASS")\n')
        marker.unlink(missing_ok=True)
        r = run(pkg, manifest, board)
        b = json.loads(board.read_text())
        if r.returncode == 0:
            failures.append("full board did not fail on missing synthetic corpus")
        if b["summary"].get("mode") != "full":
            failures.append("full DATA1 abort does not identify summary.mode=full")
        if b["summary"].get("aborted") != "DATA1":
            failures.append("full board did not abort at DATA1")
        if marker.exists():
            failures.append("full board executed a data-dependent check after DATA1 failed")

    print("control-plane success without data : ok" if not failures else "control-plane regression detected")
    for failure in failures:
        print("  FAIL", failure)
    print("RESULT:", "PASS" if not failures else f"FAIL {len(failures)}")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
