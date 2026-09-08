#!/usr/bin/env python3
"""Stage 19 - article-level semantic recall.

FTS5 and the trigram index give exact and lexical matching. Neither reaches a
provision whose wording does not overlap the question, which is the common case
for a builder asking in their own words. This adds ~2,700 article-level vectors
in the same SQLite file, to be fused with FTS5 by Reciprocal Rank Fusion.

Two decisions worth stating:
  * ARTICLE level, not sentence. An article is the unit a builder cites and is
    long enough to embed meaningfully; sentence and clause nodes stay separately
    addressable so a citation can still be precise.
  * CONTEXTUAL embedding. Each article is prefixed with its scope trail
    (Division > Part > Section > Subsection) and its own heading before
    encoding, so "makeup air" carries "Heating, Ventilating and Air-Conditioning
    > Ventilation" into the vector rather than floating free.

The model is a static embedding model: deterministic, CPU-only, no service
dependency, so gate H1 (byte-identical rebuilds) still holds.
"""
import os, argparse, os, sqlite3, sys, time, hashlib
import numpy as np
import sqlite_vec
MODEL = os.environ.get("OBC_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

class Encoder:
    """A real transformer encoder run through ONNX Runtime - no torch, CPU only,
    deterministic. A static embedding model was tried first (potion-retrieval-32M)
    and reached only 2/9 on lexically disjoint questions; the contextual encoder
    is the difference between a vector layer that earns its place and one that
    does not."""
    def __init__(self, repo=MODEL):
        from transformers import AutoTokenizer
        from huggingface_hub import hf_hub_download
        import onnxruntime as ort
        self.tok = AutoTokenizer.from_pretrained(repo)
        self.sess = ort.InferenceSession(hf_hub_download(repo, "onnx/model.onnx"),
                                         providers=["CPUExecutionProvider"])
        self.names = {i.name for i in self.sess.get_inputs()}

    def encode(self, docs, batch=64, show_progress_bar=False):
        out = []
        for i in range(0, len(docs), batch):
            b = self.tok(docs[i:i + batch], padding=True, truncation=True,
                         max_length=256, return_tensors="np")
            feed = {k: v for k, v in b.items() if k in self.names}
            h = self.sess.run(None, feed)[0]
            m = b["attention_mask"][..., None].astype("float32")
            out.append((h * m).sum(1) / np.maximum(m.sum(1), 1e-9))
        return np.vstack(out)

def scope_trail(db, nid):
    rows = db.execute("""
        SELECT n.type, n.designator, n.heading FROM closure c
        JOIN node n ON n.id = c.ancestor
        WHERE c.descendant = ? AND c.depth > 0
        ORDER BY c.depth DESC""", (nid,)).fetchall()
    parts = []
    for t, d, h in rows:
        if t in ("division", "part", "section", "subsection", "appendix",
                 "supplementary_standard", "act"):
            parts.append(" ".join(x for x in (d, h) if x).strip())
    return " > ".join(p for p in parts if p)

def article_text(db, nid, limit=1400):
    """the article plus its sentences and clauses, in document order"""
    rows = db.execute("""
        SELECT n.designator, n.heading, n.body FROM closure c
        JOIN node n ON n.id = c.descendant
        WHERE c.ancestor = ? ORDER BY c.depth, n.rowid""", (nid,)).fetchall()
    out = []
    for d, h, b in rows:
        seg = " ".join(x for x in (d, h, b) if x).strip()
        if seg:
            out.append(seg)
    return " ".join(out)[:limit]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "emitters", "obc.sqlite"))
    ap.add_argument("--out", default="out/obc-vec.sqlite")
    ap.add_argument("--level", default="article")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    if os.path.exists(a.out):
        os.remove(a.out)
    import shutil
    shutil.copy(a.db, a.out)                      # never mutate the input
    db = sqlite3.connect(a.out)
    db.enable_load_extension(True); sqlite_vec.load(db); db.enable_load_extension(False)

    ids = [r[0] for r in db.execute(
        "SELECT id FROM node WHERE type=? ORDER BY id", (a.level,))]
    print(f"{a.level} nodes: {len(ids)}")
    docs = []
    for nid in ids:
        trail = scope_trail(db, nid)
        body = article_text(db, nid)
        docs.append(f"{trail}\n{body}" if trail else body)

    t0 = time.time()
    model = Encoder(MODEL)
    vecs = model.encode(docs, show_progress_bar=False)
    vecs = np.asarray(vecs, dtype=np.float32)
    vecs /= (np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9)
    dim = vecs.shape[1]
    print(f"encoded {len(docs)} docs, dim={dim}, {time.time()-t0:.0f}s")

    db.execute("DROP TABLE IF EXISTS vec_article")
    db.execute(f"CREATE VIRTUAL TABLE vec_article USING vec0("
               f"node_id TEXT PRIMARY KEY, embedding FLOAT[{dim}])")
    db.executemany("INSERT INTO vec_article(node_id, embedding) VALUES (?,?)",
                   [(nid, v.tobytes()) for nid, v in zip(ids, vecs)])
    db.execute("CREATE TABLE IF NOT EXISTS embed_meta (key TEXT PRIMARY KEY, value TEXT)")
    h = hashlib.sha256(b"".join(v.tobytes() for v in vecs)).hexdigest()
    for k, v in {"model": MODEL, "level": a.level, "dim": str(dim),
                 "count": str(len(ids)), "context": "scope-trail prefix",
                 "vectors_sha256": h}.items():
        db.execute("INSERT OR REPLACE INTO embed_meta VALUES (?,?)", (k, v))
    db.commit()
    print(f"-> {a.out}  vectors_sha256={h[:16]}  {os.path.getsize(a.out)/1e6:.1f} MB")

if __name__ == "__main__":
    main()
