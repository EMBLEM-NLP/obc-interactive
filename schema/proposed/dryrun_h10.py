#!/usr/bin/env python3
"""
dryrun_h10.py - exercise the proposed S0 H10 control without the real graph.

`harden/checks/check35_controls.py` is protected and was not edited, and
`emitters/obc-mod.sqlite` is absent from this container, so the control in
`check35_A4_control.py.txt` could not be registered or run for real. This
reproduces part 1 of check35's loop exactly - copy the db, mutate the copy,
re-measure - against a synthetic fixture with the same table shape as
stage15_sqlite.py + stage18 + stage20. It contains no Code text.

This is a dry run. It proves the control is wired correctly; it does not prove
S0. Once the data lands, apply the patch and run the real thing:

    python3 harden/checks/check35_controls.py --db emitters/obc-mod.sqlite

    python3 schema/proposed/dryrun_h10.py
"""
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG = os.path.normpath(os.path.join(_HERE, "..", ".."))
# check36 is still at its proposed path; when it is installed this becomes
# harden/checks/check36_schema.py and the control uses that path.
CHECK36 = os.path.join(_HERE, "check36_schema.py")


def metric_schema(db, **kw):
    r = subprocess.run([sys.executable, CHECK36, "--db", db, "--json"],
                       cwd=_PKG, capture_output=True, text=True, timeout=600)
    line = next((l for l in r.stdout.splitlines() if l.startswith("JSON ")), None)
    d = json.loads(line[5:]) if line else {}
    d["exit_zero"] = 1.0 if r.returncode == 0 else 0.0
    for k in ("conforms", "declared_type_share", "declared_kind_share"):
        d.setdefault(k, 0.0)
    return d


def mut_inject_undeclared_type(path):
    c = sqlite3.connect(path)
    rid = c.execute("SELECT COALESCE(MAX(rowid), 0) + 1 FROM node").fetchone()[0]
    c.execute("INSERT INTO node (rowid, id, permalink, volume, type, body) "
              "VALUES (?,?,?,?,?,?)",
              (rid, "X/undeclared", "X/undeclared", 1, "sched_ule", "x"))
    c.commit()
    c.close()
    return "one node injected with type 'sched_ule', absent from the NodeType enum"


def fixture(path):
    db = sqlite3.connect(path)
    db.executescript("""
    CREATE TABLE node (rowid INTEGER PRIMARY KEY, id TEXT UNIQUE NOT NULL,
      permalink TEXT, volume INTEGER, type TEXT NOT NULL, number TEXT,
      designator TEXT, heading TEXT, body TEXT, parent TEXT, depth INTEGER,
      page INTEGER, bbox TEXT, modality TEXT);
    CREATE TABLE ref (src TEXT, dst TEXT, kind TEXT, text TEXT, reason TEXT);
    CREATE TABLE term (src TEXT, dst TEXT, term TEXT);
    CREATE TABLE term_resolved (src TEXT, dst TEXT, term TEXT, blob TEXT, how TEXT);
    """)
    rows = [("B", "division", None), ("B/9", "part", "B"),
            ("B/9/9.23", "section", "B/9"), ("B/9/9.23.2", "subsection", "B/9/9.23"),
            ("B/9/9.23.2.8", "article", "B/9/9.23.2"),
            ("B/9/9.23.2.8/(1)", "sentence", "B/9/9.23.2.8"),
            ("B/9/9.23.2.8/(1)/(a)", "clause", "B/9/9.23.2.8/(1)"),
            ("DEF/secondary-suite", "defined_term", "B/9/9.23.2.8/(1)"),
            ("B/9/table/9.23.2.8", "table", "B/9/9.23.2")]
    for i, (nid, t, p) in enumerate(rows, 1):
        db.execute("INSERT INTO node (rowid,id,permalink,volume,type,parent,body) "
                   "VALUES (?,?,?,1,?,?,'x')", (i, nid, nid, t, p))
    db.executemany("INSERT INTO ref VALUES (?,?,?,?,?)", [
        ("B/9/9.23.2.8/(1)", "B/9/9.23.2", "code_ref", "9.23.2.", "exact"),
        ("B/9/9.23.2.8/(1)", "B/9/table/9.23.2.8", "cap_ref", "Table 9.23.2.8.", "exact"),
        ("B/9/9.23.2.8/(1)", None, "std", "CSA A23.1", "not-in-Table-1.3.1.2")])
    db.execute("INSERT INTO term VALUES ('B/9/9.23.2.8/(1)','B/9/9.23.2.8/(1)','suite')")
    db.execute("INSERT INTO term_resolved VALUES "
               "('B/9/9.23.2.8/(1)','DEF/secondary-suite','suite','x','exact')")
    db.commit()
    db.close()


REGISTRY = [
    ("S0 declared types", "conforms",  1.00, metric_schema, mut_inject_undeclared_type),
    ("S0 exit code",      "exit_zero", 1.00, metric_schema, mut_inject_undeclared_type),
]


def main():
    tmp = tempfile.mkdtemp()
    base = os.path.join(tmp, "fixture.sqlite")
    fixture(base)
    print("SYNTHETIC FIXTURE - this is a dry run, not gate S0.\n")
    print(f"{'gate':<20}{'floor':>7}{'real':>9}{'mutated':>10}  verdict")
    print("-" * 62)
    fails = []
    for gate, key, floor, metric, mutate in REGISTRY:
        real = metric(base)[key]
        path = os.path.join(tmp, "mutated.sqlite")
        shutil.copy(base, path)
        note = mutate(path)
        bad = metric(path)[key]
        os.remove(path)
        ok = bad < floor <= real
        verdict = ("ok" if ok else
                   "METRIC NEVER FAILS" if bad >= floor else "real below floor")
        print(f"{gate:<20}{floor:>7.0%}{real:>9.1%}{bad:>10.1%}  {verdict}")
        print(f"{'':<20}mutation: {note}")
        if not ok:
            fails.append(f"{gate}: real {real:.1%}, mutated {bad:.1%}")
    shutil.rmtree(tmp, ignore_errors=True)
    print("\nRESULT:", "PASS" if not fails else "FAIL " + "; ".join(fails))
    print("This proves the control is wired. S0 itself needs "
          "emitters/obc-mod.sqlite and 27,421 real nodes.")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
