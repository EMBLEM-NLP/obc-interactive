#!/usr/bin/env python3
"""B0 — no-data regression/control for Track B model-correctness refactor.

This check uses a synthetic SQLite graph so it runs before DATA1 on a clean
clone. It proves the architectural invariants introduced by B1/B2/B3/B4 are
wired into executable code rather than existing only as comments.
"""

from __future__ import annotations

import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "retrieval" / "lib"
sys.path.insert(0, str(LIB))
from text_projection import (  # noqa: E402
    FLAT_BODY_CHARS,
    bound_table_ids,
    owns_table,
    projected_body,
    table_text,
)


def synthetic_db() -> sqlite3.Connection:
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE node (
      rowid INTEGER PRIMARY KEY,
      id TEXT UNIQUE, type TEXT, designator TEXT, heading TEXT, body TEXT,
      parent TEXT
    );
    CREATE TABLE closure (ancestor TEXT, descendant TEXT, depth INTEGER);
    CREATE TABLE ref (src TEXT, dst TEXT, kind TEXT, text TEXT, reason TEXT);
    CREATE TABLE cell (
      table_id TEXT, page INTEGER, r INTEGER, c INTEGER,
      rowspan INTEGER, colspan INTEGER, text TEXT
    );
    INSERT INTO node VALUES
      (1,'B/3','part','3.','','',NULL),
      (2,'B/3/3.1.17.1','article','3.1.17.1.','Occupant Load Determination','', 'B/3'),
      (3,'B/3/3.1.17.1/(1)','sentence','(1)','', '', 'B/3/3.1.17.1'),
      (4,'B/3/table/3.1.17.1','table','Table 3.1.17.1.','', '', 'B/3');
    INSERT INTO closure VALUES
      ('B/3','B/3',0),
      ('B/3','B/3/3.1.17.1',1),
      ('B/3','B/3/3.1.17.1/(1)',2),
      ('B/3','B/3/table/3.1.17.1',1),
      ('B/3/3.1.17.1','B/3/3.1.17.1',0),
      ('B/3/3.1.17.1','B/3/3.1.17.1/(1)',1),
      ('B/3/3.1.17.1/(1)','B/3/3.1.17.1/(1)',0),
      ('B/3/table/3.1.17.1','B/3/table/3.1.17.1',0);
    INSERT INTO ref VALUES
      ('B/3/table/3.1.17.1','B/3/3.1.17.1/(1)','forms_part_of','Forming Part of','exact');
    INSERT INTO cell VALUES
      ('B/3/table/3.1.17.1',232,0,0,1,1,'Type of Use'),
      ('B/3/table/3.1.17.1',232,1,0,1,1,'standing space');
    """)
    long_body = "intro " + ("flattened-table-value " * 80)
    c.execute("UPDATE node SET body=? WHERE id='B/3/3.1.17.1'", (long_body,))
    return c


def main() -> int:
    failures = []
    c = synthetic_db()

    # B2: parent stays the structural Part while the semantic table binding is
    # a first-class edge.
    parent = c.execute(
        "SELECT parent FROM node WHERE id='B/3/table/3.1.17.1'"
    ).fetchone()[0]
    if parent != "B/3":
        failures.append(f"table containment drifted: parent={parent!r}")
    bound = bound_table_ids(c, "B/3/3.1.17.1")
    if bound != ["B/3/table/3.1.17.1"]:
        failures.append(f"forms_part_of traversal failed: {bound}")

    # B1: ownership must follow the binding edge, not containment. Long flat
    # parent text is trimmed and structured cells remain available once.
    if not owns_table(c, "B/3/3.1.17.1"):
        failures.append("article does not own table through forms_part_of")
    original = c.execute(
        "SELECT body FROM node WHERE id='B/3/3.1.17.1'"
    ).fetchone()[0]
    projected, suppressed = projected_body(
        c, "B/3/3.1.17.1", "article", original
    )
    if not suppressed or len(projected) > FLAT_BODY_CHARS:
        failures.append("flattened article tail was not suppressed")
    cells = table_text(c, bound)
    if "standing space" not in cells:
        failures.append("structured table cells were not preserved")

    # Schema declares the relation and its reverse.
    schema = yaml.safe_load((ROOT / "schema" / "obc.linkml.yaml").read_text())
    forms = schema["enums"]["EdgeKind"]["permissible_values"].get("forms_part_of")
    reverse = ((forms or {}).get("annotations") or {}).get("reverse")
    if not forms or not reverse:
        failures.append("schema does not declare forms_part_of with a reverse")

    # Static guards for the pipeline pieces that cannot run without the Crown
    # source PDFs. These are intentionally narrow invariants, not substitute
    # integration tests.
    stage5 = (ROOT / "pipeline" / "stage5_bind.py").read_text()
    if 'parent = pid' not in stage5 or '"forms_part_of": target' not in stage5:
        failures.append("stage5 no longer separates containment from binding")
    stage7 = (ROOT / "pipeline" / "stage7_refs.py").read_text()
    if 'chunks.append(("h", n["heading"]))' not in stage7:
        failures.append("stage7 no longer scans headings")
    stage12 = (ROOT / "pipeline" / "vol2" / "stage12_links2.py").read_text()
    if 'r.get("chunk") == "h"' not in stage12:
        failures.append("cross-volume link emitter no longer handles heading refs")
    stage15 = (ROOT / "pipeline" / "emitters" / "stage15_sqlite.py").read_text()
    if '"forms_part_of"' not in stage15:
        failures.append("SQLite emitter no longer emits table-binding relation")
    if 'time.gmtime(source_epoch)' not in stage15 or 'DEFAULT_SOURCE_DATE_EPOCH' not in stage15:
        failures.append("SQLite emitter metadata can fall back to wall-clock time")

    # Every touched Python file must at least compile in a data-less clone.
    touched = [
        "pipeline/stage5_bind.py",
        "pipeline/stage7_refs.py",
        "pipeline/stage8_links.py",
        "pipeline/vol2/stage12_links2.py",
        "pipeline/emitters/stage15_sqlite.py",
        "pipeline/emitters/stage16_markdown.py",
        "pipeline/emitters/stage17_html.py",
        "retrieval/lib/text_projection.py",
        "retrieval/lib/obc_context.py",
        "retrieval/stage19_embed.py",
        "harden/checks/check36_schema.py",
    ]
    with tempfile.TemporaryDirectory(prefix="obc-pyc-") as cache:
        env = dict(os.environ, PYTHONPYCACHEPREFIX=cache)
        for rel in touched:
            r = subprocess.run(
                [sys.executable, "-m", "py_compile", str(ROOT / rel)],
                capture_output=True, text=True, env=env,
            )
            if r.returncode:
                failures.append(f"py_compile failed {rel}: {r.stderr.strip()}")

    if failures:
        for failure in failures:
            print("FAIL", failure)
        print(f"RESULT: FAIL {len(failures)}")
        return 1
    print("RESULT: PASS — B1/B2/B3/B4 refactor invariants and negative surfaces are wired")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
