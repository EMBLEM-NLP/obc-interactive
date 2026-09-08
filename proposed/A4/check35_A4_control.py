PROPOSED ADDITION TO harden/checks/check35_controls.py — H10 control for gate S0
================================================================================

HANDOFF NOTE. `harden/checks/check35_controls.py` is inside the protected set and
was NOT edited. This file is the proposed patch, for a human to review and apply.
Until it is applied, S0 is a ratio gate with no registered mutation and is
therefore void under PROTOCOL.md R-H10, however green check36 reports.

It has not been run against `emitters/obc-mod.sqlite`, which is absent from this
container. It WAS dry-run against a synthetic fixture with the same table shape
as stage15_sqlite.py + stage18 + stage20 — see the transcript at the bottom.

Why part 1 of the registry and not part 2
----------------------------------------
Part 2 (`SUBPROCESS_CONTROLS`) materialises a working set from `verify/<scope>/`;
there is no scope that hands a check a copy of `obc-mod.sqlite`, and inventing one
means editing `run_subprocess_controls()`, a larger change to a protected file.
Part 1's loop already does exactly what is needed for a data mutation: copy the
db, mutate the copy, re-measure. The usual objection to part 1 is that a metric
function tests your reimplementation rather than the shipped check — check33's
error, one level up. `metric_schema` below avoids that by *shelling out to the
shipped check36_schema.py* and parsing the JSON line it prints. The metric is the
check's own output, and `exit_zero` carries the check's own exit code, so both
directions of the H10 contract are asserted through the existing loop:

    S0 declared types  real 100.0%  mutated 0.0%   ->  untouched passes, mutated fails
    S0 exit code       real 100.0%  mutated 0.0%   ->  exit 0 becomes exit non-zero

--------------------------------------------------------------------------------
1. Add to part 1, beside the other metric functions.
--------------------------------------------------------------------------------

def metric_schema(db, **kw):
    """S0. Runs the SHIPPED check36_schema.py as a black box and parses the
    JSON line it prints. Deliberately not a reimplementation of check36's
    measurement: a control that scores my copy of the metric proves my copy
    works, which is check33's error one level up.

    `conforms` and `exit_zero` are both 1.0 or 0.0, so the floor of 1.00 reads
    cleanly at the printer's one-decimal precision. A share-of-27421 metric
    would render a single injected node as '100.0%' in the table while the
    comparison silently used 0.999963 — green to the eye, correct in the code,
    and exactly the kind of gap this file exists to close."""
    script = os.path.join(_PKG, "harden", "checks", "check36_schema.py")
    r = subprocess.run([sys.executable, script, "--db", db, "--json"],
                       cwd=_PKG, capture_output=True, text=True, timeout=600)
    line = next((l for l in r.stdout.splitlines() if l.startswith("JSON ")), None)
    d = json.loads(line[5:]) if line else {}
    d["exit_zero"] = 1.0 if r.returncode == 0 else 0.0
    for k in ("conforms", "declared_type_share", "declared_kind_share"):
        d.setdefault(k, 0.0)
    return d


def mut_inject_undeclared_type(path):
    """Inject one node carrying a type that is not in the NodeType enum.

    The mutation targets the MECHANISM — the `type` column that
    pipeline/emitters/stage15_sqlite.py emits — and never the ground truth,
    which is `schema/obc.linkml.yaml`. Editing the enum instead would move the
    ruler and leave the ratio at 1.0, the same class of error as deleting the
    `ref` table to break a resolution ratio.

    INSERT, not UPDATE: gate S0's claim is that an undeclared type *fails
    validation*, and an injected node is the literal form of that claim. It
    also leaves every existing row untouched, so nothing else the check reads
    changes."""
    c = sqlite3.connect(path)
    rid = c.execute("SELECT COALESCE(MAX(rowid), 0) + 1 FROM node").fetchone()[0]
    c.execute("INSERT INTO node (rowid, id, permalink, volume, type, body) "
              "VALUES (?,?,?,?,?,?)",
              (rid, "X/undeclared", "X/undeclared", 1, "sched_ule", "x"))
    c.commit()
    c.close()
    return "one node injected with type 'sched_ule', absent from the NodeType enum"


--------------------------------------------------------------------------------
2. Add to REGISTRY (part 1). Two entries: one per direction of the contract.
--------------------------------------------------------------------------------

REGISTRY = [
    ("R4a reachability", "C1", 0.99, metric_bundle, mut_no_expansion, {"hops": 0}),
    ("R4b delivery",     "C2", 0.95, metric_bundle, mut_starve_budget, {"budget": 200}),
    ("R4c usability",    "C3", 0.99, metric_bundle, mut_drop_term_resolved, None),
    ("R8 modality",      "prohibition_share", 0.02, metric_modality,
     mut_ablate_prohibition, None),
+   ("S0 declared types", "conforms", 1.00, metric_schema,
+    mut_inject_undeclared_type, None),
+   ("S0 exit code",      "exit_zero", 1.00, metric_schema,
+    mut_inject_undeclared_type, None),
]

No other change is required: the part 1 loop already copies `a.db` to a temp
path, applies the mutation to the copy, and re-measures, because `kw is None`.

--------------------------------------------------------------------------------
3. Dry-run transcript (synthetic fixture, this container, 2026-09-08)
--------------------------------------------------------------------------------

  gate                  floor     real   mutated  verdict
  S0 declared types      100%   100.0%      0.0%  ok
                        mutation: one node injected with type 'sched_ule', absent from the NodeType enum
  S0 exit code           100%   100.0%      0.0%  ok
                        mutation: one node injected with type 'sched_ule', absent from the NodeType enum

Reproduced with `schema/proposed/dryrun_h10.py`. The fixture is nine synthetic
rows with the shape of stage15's `node`/`ref`/`term`/`term_resolved`; it contains
no Code text. When `emitters/obc-mod.sqlite` is present this must be re-run for
real, against 27,421 nodes, before S0 may be ticked.

--------------------------------------------------------------------------------
4. What could go wrong when this is run for real
--------------------------------------------------------------------------------

* If `real` reads below 1.00 for "S0 declared types", the enum transcription in
  schema/obc.linkml.yaml is incomplete — a node type exists in the emitted graph
  that no pipeline literal revealed. check36 prints the offending value and its
  row count. That is a finding for A4, not a reason to widen the enum silently.
* If the entry reads NEVER FAILS, check the INSERT actually landed: obc-mod.sqlite
  carries AFTER INSERT triggers on `node` feeding `node_fts`, and a trigger error
  would roll the insert back.
* If it reads NEVER PASSES with exit 2, check36 was not found at
  harden/checks/check36_schema.py — it is still sitting in schema/proposed/.
