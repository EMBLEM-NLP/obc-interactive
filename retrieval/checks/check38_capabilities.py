#!/usr/bin/env python3
"""
check38_capabilities.py - G2: the agent's `cannot` list is computed, and
every probe responds to the graph.

A capability statement an agent trusts must be falsifiable like any other
gate. For each probe in CANNOT_PROBES: assert it fires on the shipped
database, then seed the capability into a copy and assert it clears. A probe
that fires on both is a constant with SQL decoration.

    python3 check38_capabilities.py --db ../emitters/obc-mod.sqlite
"""
import argparse, os, shutil, sqlite3, sys, tempfile
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "lib"))
import obc_agent_tools as T

# how to seed each capability into a copy of the DB
SEED = {
    "applicability": "INSERT INTO node (id,permalink,volume,type,heading,body,depth,page) VALUES ('OCC/C','OCC/C',1,'occupancy','Group C',' ',1,1)",
    "objectives":    "INSERT INTO node (id,permalink,volume,type,heading,body,depth,page) VALUES ('OBJ/OS1','OBJ/OS1',1,'objective','OS1',' ',1,1)",
    "temporal":      "CREATE TABLE in_force (node TEXT, from_date TEXT, to_date TEXT)",
    "rules":         "CREATE TABLE rule (id TEXT PRIMARY KEY, provision TEXT, expr TEXT)",
    "heading_notes": """INSERT INTO ref (src, dst, kind, text, reason)
                        SELECT n.id, 'APPA/A-seed', 'note', 'See Note', 'seeded' FROM node n
                        WHERE n.heading LIKE '%See Note%'""",
}

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--db", default=os.path.join(_HERE, "..", "..", "emitters", "obc-mod.sqlite"))
    a = ap.parse_args()
    fails = []
    T.DB_PATH = a.db; T._db = None
    live = {e["id"]: e for e in T.compute_cannot(T.db())}
    print(f"probes firing on the shipped db: {sorted(live)}")
    for pid, sql, _, _ in T.CANNOT_PROBES:
        if pid not in SEED:
            print(f"   {pid:<14} (no seed defined; semantic clears when G1 lands)"); continue
        if pid not in live:
            fails.append(f"{pid}: does not fire on the shipped db but the capability is absent"); continue
        tmp = tempfile.mkdtemp(); cp = os.path.join(tmp, "seeded.sqlite"); shutil.copy(a.db, cp)
        c = sqlite3.connect(cp); c.execute(SEED[pid]); c.commit()
        after = {e["id"] for e in T.compute_cannot(c)}
        ok = pid not in after
        print(f"   {pid:<14} fires={'yes':<4} seeded->clears={'yes' if ok else 'NO'}")
        if not ok: fails.append(f"{pid}: still fires after seeding the capability - constant, not a probe")
        shutil.rmtree(tmp, ignore_errors=True)
    if "official" not in live: fails.append("the 'official' line must always be present")
    print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
