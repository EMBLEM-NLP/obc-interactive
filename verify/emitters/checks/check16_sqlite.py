#!/usr/bin/env python3
"""Check 16 - the SQLite emitter.

Proves the three queries the model was built to answer actually run, that FTS5
ranks and highlights, that clause-number search works despite unicode61
fragmenting it, and that row counts match the graph.
"""
import sys, os, sqlite3, os, gzip, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from emit_common import load_graph
DB = "out/obc.sqlite"
if not os.path.exists(DB):
    print("RESULT: FAIL database missing"); sys.exit(1)
nodes, order, _ = load_graph()
db = sqlite3.connect(DB)
q = lambda s, *a: db.execute(s, a).fetchall()
fails = []

n_db = q("SELECT count(*) FROM node")[0][0]
if n_db != len(order): fails.append(f"node count {n_db} != graph {len(order)}")
print(f"nodes            : {n_db}")

# 1. what cites this article
cites = q("""SELECT count(*) FROM ref WHERE dst=?""", "B/3/3.1.4.7")[0][0]
print(f"citations of B/3/3.1.4.7 : {cites}")
if cites == 0: fails.append("citation reverse lookup returned nothing")

# 2. what did O. Reg. 5/25 change
changed = q("""SELECT n.id, n.designator FROM amendment a JOIN node n ON n.id=a.node
               WHERE a.instrument='5/25' ORDER BY n.id""")
print(f"provisions changed by O. Reg. 5/25 : {len(changed)}  {[c[0] for c in changed][:4]}")
if not changed: fails.append("amendment query returned nothing")

# 3. a provision with its defined terms
dt = q("""SELECT t.term, t.dst FROM term t WHERE t.src=? ORDER BY t.term""",
       "B/9/9.10.16.1/(1)")
print(f"defined terms in B/9/9.10.16.1/(1) : {[d[0] for d in dt][:4]}")
if not dt: fails.append("defined-term query returned nothing")

# 4. subtree via the closure table, no recursive CTE
sub = q("SELECT count(*) FROM closure WHERE ancestor=?", "B/9")[0][0]
print(f"descendants of B/9 (closure)      : {sub}")
if sub < 1000: fails.append("closure table looks wrong")

# 5. FTS5 ranking + snippet
hits = q("""SELECT n.id, snippet(node_fts,2,'[',']','…',8), bm25(node_fts)
            FROM node_fts JOIN node n ON n.rowid=node_fts.rowid
            WHERE node_fts MATCH 'fire AND separation'
            ORDER BY bm25(node_fts) LIMIT 3""")
print(f"FTS 'fire AND separation'         : {len(hits)} hits, top {hits[0][0] if hits else None}")
if len(hits) < 3: fails.append("FTS5 search returned too few hits")
if hits and "[" not in hits[0][1]: fails.append("snippet() did not highlight")

# 6. clause-number search - the case unicode61 cannot do
tri = q("""SELECT count(*) FROM node_tri WHERE node_tri MATCH '"9.10.16.1"'""")[0][0]
print(f"trigram search '9.10.16.1'        : {tri} rows")
if tri == 0: fails.append("trigram clause-number search failed")
sb = q("""SELECT count(*) FROM node_tri WHERE node_tri MATCH '"SB-3"'""")[0][0]
print(f"trigram search 'SB-3'             : {sb} rows")
if sb == 0: fails.append("trigram standard-designator search failed")

# 7. licence and currency must be carried in the artefact
m = dict(q("SELECT key, value FROM meta"))
for k in ("current_to", "through", "notice", "copyright", "licence"):
    if not m.get(k): fails.append(f"meta.{k} missing")
print(f"current to {m.get('current_to')} through {m.get('through')}")

# 8. referential integrity
bad = q("""SELECT count(*) FROM ref WHERE dst IS NOT NULL
           AND dst NOT IN (SELECT id FROM node)""")[0][0]
bad += q("""SELECT count(*) FROM term WHERE dst NOT IN (SELECT id FROM node)""")[0][0]
print(f"dangling foreign keys             : {bad}")
if bad: fails.append(f"{bad} dangling references")

print(f"   size {os.path.getsize(DB)/1e6:.1f} MB")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
