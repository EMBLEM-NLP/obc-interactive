#!/usr/bin/env python3
"""Emitter 1 - SQLite with FTS5.

Design follows the research: external-content FTS5 so text is not duplicated,
bm25 ranking with snippet/highlight, unicode61+porter for prose PLUS a trigram
index because unicode61 fragments clause numbers like 9.10.16.1. and SB-3.
Hierarchy is an adjacency list plus a closure table - the corpus is read-heavy
and near-static between editions, so the closure table is cheap and turns
"all descendants" into an indexed join instead of a recursive CTE.
"""
import os, sqlite3, json, os, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from emit_common import (load_graph, permalink, node_text, designator,
                         CURRENT_TO_ISO, THROUGH, NOTICE, COPYRIGHT, LICENCE)

OUT = "out/obc.sqlite"
t0 = time.time()
nodes, order, meta = load_graph()
if os.path.exists(OUT):
    os.remove(OUT)
db = sqlite3.connect(OUT)
db.executescript("""
PRAGMA journal_mode=WAL;
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE node (
  rowid      INTEGER PRIMARY KEY,
  id         TEXT UNIQUE NOT NULL,
  permalink  TEXT NOT NULL,
  volume     INTEGER,
  type       TEXT NOT NULL,
  number     TEXT,
  designator TEXT,
  heading    TEXT,
  body       TEXT,
  parent     TEXT,
  depth      INTEGER,
  page       INTEGER,
  bbox       TEXT
);
CREATE INDEX node_parent  ON node(parent);
CREATE INDEX node_type    ON node(type);
CREATE INDEX node_number  ON node(number);
CREATE INDEX node_page    ON node(volume, page);

-- closure table: ancestor/descendant with depth, for constant-time subtrees
CREATE TABLE closure (
  ancestor   TEXT NOT NULL,
  descendant TEXT NOT NULL,
  depth      INTEGER NOT NULL,
  PRIMARY KEY (ancestor, descendant)
);
CREATE INDEX closure_desc ON closure(descendant);

CREATE TABLE ref (
  src TEXT NOT NULL, dst TEXT, kind TEXT, text TEXT, reason TEXT
);
CREATE INDEX ref_src ON ref(src);
CREATE INDEX ref_dst ON ref(dst);

CREATE TABLE term (
  src TEXT NOT NULL, dst TEXT NOT NULL, term TEXT NOT NULL
);
CREATE INDEX term_src  ON term(src);
CREATE INDEX term_dst  ON term(dst);
CREATE INDEX term_name ON term(term);

CREATE TABLE amendment (
  node TEXT NOT NULL, marker TEXT, kind TEXT, instrument TEXT, effective TEXT
);
CREATE INDEX amendment_node ON amendment(node);
CREATE INDEX amendment_instr ON amendment(instrument);

CREATE TABLE cell (
  table_id TEXT NOT NULL, page INTEGER, r INTEGER, c INTEGER,
  rowspan INTEGER, colspan INTEGER, text TEXT
);
CREATE INDEX cell_table ON cell(table_id);
""")

rid = {}
rows = []
for i, nid in enumerate(order, start=1):
    n = nodes[nid]
    rid[nid] = i
    pv = (n.get("provenance") or [{}])[0]
    rows.append((i, nid, permalink(nid), n.get("volume", 1), n["type"],
                 n.get("number"), designator(n), n.get("heading"),
                 node_text(n), n.get("parent"), None,
                 pv.get("page"), json.dumps(pv.get("bbox")) if pv.get("bbox") else None))
db.executemany("INSERT INTO node VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)

# depth + closure
depth = {}
def d_of(nid):
    if nid in depth:
        return depth[nid]
    p = nodes[nid].get("parent")
    depth[nid] = 0 if not p or p not in nodes else d_of(p) + 1
    return depth[nid]
sys.setrecursionlimit(10000)
clos = []
for nid in order:
    d = d_of(nid)
    db.execute("UPDATE node SET depth=? WHERE id=?", (d, nid))
    cur, k = nid, 0
    while cur:
        clos.append((cur, nid, k))
        cur = nodes[cur].get("parent") if cur in nodes else None
        k += 1
db.executemany("INSERT OR IGNORE INTO closure VALUES (?,?,?)", clos)

refs = [(nid, r.get("target"), r["kind"], r.get("text"), r.get("why"))
        for nid in order for r in nodes[nid].get("refs", [])]
db.executemany("INSERT INTO ref VALUES (?,?,?,?,?)", refs)
terms = [(nid, t["target"], t["term"])
         for nid in order for t in nodes[nid].get("terms", [])]
db.executemany("INSERT INTO term VALUES (?,?,?)", terms)
amds = [(nid, a["marker"], a["kind"], a.get("instrument"), a.get("effective"))
        for nid in order for a in nodes[nid].get("amendment", [])]
db.executemany("INSERT INTO amendment VALUES (?,?,?,?,?)", amds)
cells = [(nid, c.get("page"), c["r"], c["c"], c["rowspan"], c["colspan"], c["text"])
         for nid in order for c in (nodes[nid].get("grid") or [])]
db.executemany("INSERT INTO cell VALUES (?,?,?,?,?,?,?)", cells)

# FTS5, external content over node
db.executescript("""
CREATE VIRTUAL TABLE node_fts USING fts5(
  designator, heading, body,
  content='node', content_rowid='rowid',
  tokenize="porter unicode61 remove_diacritics 2"
);
INSERT INTO node_fts(rowid, designator, heading, body)
  SELECT rowid, designator, heading, body FROM node;
CREATE TRIGGER node_ai AFTER INSERT ON node BEGIN
  INSERT INTO node_fts(rowid, designator, heading, body)
  VALUES (new.rowid, new.designator, new.heading, new.body);
END;
CREATE TRIGGER node_ad AFTER DELETE ON node BEGIN
  INSERT INTO node_fts(node_fts, rowid, designator, heading, body)
  VALUES ('delete', old.rowid, old.designator, old.heading, old.body);
END;
CREATE TRIGGER node_au AFTER UPDATE ON node BEGIN
  INSERT INTO node_fts(node_fts, rowid, designator, heading, body)
  VALUES ('delete', old.rowid, old.designator, old.heading, old.body);
  INSERT INTO node_fts(rowid, designator, heading, body)
  VALUES (new.rowid, new.designator, new.heading, new.body);
END;
""")
# trigram index: unicode61 splits 9.10.16.1. into fragments, so substring
# search for a clause number needs its own tokenizer
try:
    db.executescript("""
    CREATE VIRTUAL TABLE node_tri USING fts5(
      id, designator, body, tokenize="trigram");
    INSERT INTO node_tri(rowid, id, designator, body)
      SELECT rowid, id, designator, body FROM node;
    """)
    tri = True
except sqlite3.OperationalError as e:
    tri = False
    print("trigram tokenizer unavailable:", e)

for k, v in {"current_to": CURRENT_TO_ISO, "through": THROUGH,
             "notice": NOTICE, "copyright": COPYRIGHT, "licence": LICENCE,
             "nodes": str(len(order)), "generated": time.strftime("%Y-%m-%d", time.gmtime(int(os.environ["SOURCE_DATE_EPOCH"])))
                 if os.environ.get("SOURCE_DATE_EPOCH") else time.strftime("%Y-%m-%d")}.items():
    db.execute("INSERT INTO meta VALUES (?,?)", (k, v))
db.commit()
db.executescript("PRAGMA journal_mode=DELETE; VACUUM; ANALYZE;")
db.commit()
print(f"nodes {len(order)} | closure {len(clos)} | refs {len(refs)} | "
      f"terms {len(terms)} | amendments {len(amds)} | cells {len(cells)}")
print(f"trigram index: {tri} | {os.path.getsize(OUT)/1e6:.1f} MB | {time.time()-t0:.0f}s")
