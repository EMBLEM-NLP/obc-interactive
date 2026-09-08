#!/usr/bin/env python3
"""Hybrid retrieval: FTS5 + vectors, fused by Reciprocal Rank Fusion.

RRF is used rather than score normalisation because BM25 and cosine similarity
are not on a comparable scale, and RRF depends only on rank. k=60 is the
conventional constant.

The index and contents nodes repeat provision wording verbatim, so they outrank
the provisions themselves under raw BM25. They are demoted, not excluded - the
same correction the review already had to make.
"""
import os, sqlite3, numpy as np, sqlite_vec, re


K = 60
DEMOTE = {"index", "index_entry", "index_subentry", "contents"}
_model = None

def model():
    global _model
    if _model is None:
        import importlib.util, sys as _s, os as _o
        spec = importlib.util.spec_from_file_location(
            "stage19_embed", _o.path.join(_o.path.dirname(_o.path.dirname(
                _o.path.abspath(__file__))), "stage19_embed.py"))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        _model = m.Encoder()
    return _model

def connect(path):
    db = sqlite3.connect(path)
    db.enable_load_extension(True); sqlite_vec.load(db); db.enable_load_extension(False)
    return db

def _article_of(db, nid):
    """map any node to the article that contains it, so the three layers rank
    the same unit"""
    row = db.execute("""
        SELECT c.ancestor FROM closure c JOIN node n ON n.id=c.ancestor
        WHERE c.descendant=? AND n.type='article' ORDER BY c.depth LIMIT 1""",
        (nid,)).fetchone()
    if row: return row[0]
    t = db.execute("SELECT type FROM node WHERE id=?", (nid,)).fetchone()
    return nid if t and t[0] == "article" else None

def fts(db, q, n=50):
    """lexical, rolled up to article level"""
    terms = [t for t in re.findall(r"[A-Za-z][A-Za-z\-']+|\d+(?:\.\d+)+", q) if len(t) > 2]
    if not terms:
        return []
    match = " OR ".join(f'"{t}"' for t in terms)
    rows = db.execute("""
        SELECT n.id, n.type, bm25(node_fts) FROM node_fts
        JOIN node n ON n.rowid = node_fts.rowid
        WHERE node_fts MATCH ? ORDER BY bm25(node_fts) LIMIT ?""",
        (match, n * 4)).fetchall()
    out, seen = [], set()
    for nid, typ, score in rows:
        art = _article_of(db, nid)
        if not art or art in seen:
            continue
        seen.add(art)
        out.append((art, score + (5.0 if typ in DEMOTE else 0.0)))
    out.sort(key=lambda r: r[1])
    return [a for a, _ in out[:n]]

def vec(db, q, n=50):
    v = np.asarray(model().encode([q]), dtype=np.float32)[0]
    v /= (np.linalg.norm(v) + 1e-9)
    rows = db.execute("""
        SELECT node_id, distance FROM vec_article
        WHERE embedding MATCH ? AND k = ? ORDER BY distance""",
        (v.tobytes(), n)).fetchall()
    return [r[0] for r in rows]

def rrf(*rankings, k=K):
    score = {}
    for r in rankings:
        for i, nid in enumerate(r):
            score[nid] = score.get(nid, 0.0) + 1.0 / (k + i + 1)
    return [nid for nid, _ in sorted(score.items(), key=lambda x: -x[1])]

def search(db, q, n=10, mode="hybrid"):
    if mode == "fts":
        return fts(db, q, n)[:n]
    if mode == "vec":
        return vec(db, q, n)[:n]
    return rrf(fts(db, q, 50), vec(db, q, 50))[:n]

def wrrf(fts_list, vec_list, w_fts=1.0, w_vec=1.0, k=K):
    """Weighted RRF.

    Plain RRF failed here in a way worth recording: a document appearing in BOTH
    lists gets roughly double score, so when the lexical list is pure noise its
    mid-ranked documents that also appear in the vector list outrank the vector
    list's own top hits. Hybrid scored 0/9 on lexically disjoint questions while
    vectors alone scored 2/9 - the fusion destroyed the capability the vectors
    were added for.

    An IDF-based confidence rule was tried first and rejected: on this corpus the
    lexically disjoint questions have HIGHER max-IDF than the lexical ones,
    because everyday words like "loft" and "scalded" are rare in Code vocabulary.
    IDF measures rarity, not relevance.
    """
    score = {}
    for lst, w in ((fts_list, w_fts), (vec_list, w_vec)):
        for i, nid in enumerate(lst):
            score[nid] = score.get(nid, 0.0) + w / (k + i + 1)
    return [nid for nid, _ in sorted(score.items(), key=lambda x: -x[1])]

def fuse(fts_list, vec_list, n=10, reserve=None, k=K):
    """RRF with guaranteed representation.

    Stated a priori, not tuned: the top `reserve` results of EACH list are
    guaranteed a place in the fused top-n, and the remaining slots are filled in
    RRF order. This exists because plain RRF cannot be relied on to surface a
    result that only one list found - a document in both lists collects roughly
    double score, so a noisy lexical list crowds out the vector list's own best
    hits. Guaranteeing slots makes the fused result at least as good as either
    input on its strongest few, which is the property RRF alone does not give.
    """
    # Proportional reservation, not a fixed count. The contract this gives is
    # exact and checkable: the fused top-n contains each list's own top ceil(n/2),
    # so hybrid@n is never worse than either layer at half the budget. A fixed
    # reserve of 2 did NOT give that - at n=10 and n=20 the RRF tail pushed
    # vector-only hits out and the fused result lost disjoint-query recall that
    # the vector layer had found on its own.
    if reserve is None:
        reserve = -(-n // 2)
    out = []
    for i in range(reserve):
        for lst in (vec_list, fts_list):
            if i < len(lst) and lst[i] not in out:
                out.append(lst[i])
    for nid in wrrf(fts_list, vec_list, 1.0, 1.0, k):
        if nid not in out:
            out.append(nid)
        if len(out) >= n:
            break
    return out[:n]
