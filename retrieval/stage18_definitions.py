#!/usr/bin/env python3
"""
stage18_definitions.py - split the definition blobs into individual terms.

Defect this fixes
-----------------
Article 1.4.1.2 of Division A is one sentence with a handful of clause
children, each clause holding hundreds of definitions run together as
continuous prose. The largest, A/1/1.4.1.2/(1)/(i), is 31,199 characters.
stage7 correctly resolves every italicised term to the clause that defines
it, so the graph is not wrong - but 570 distinct terms share only 6 targets.

For traversal that is harmless. For retrieval it is fatal: asking for the
definition of "secondary suite" returns 16 KB of alphabetically adjacent
definitions, and any truncation returns a different term's definition
entirely. An LLM handed that context will confidently cite the wrong rule.

What it does
------------
Splits each blob on the "<Term> means ..." pattern, emits one
`defined_term` node per definition, and repoints every `term` edge at the
specific definition instead of the blob.

Validation is structural, not statistical. Definitions inside a clause run
in alphabetical order, so a false boundary (a mid-sentence "X means")
breaks monotonicity and is rejected. That is a real oracle, not a
heuristic threshold.

Writes a new database; never mutates the input.

    python3 stage18_definitions.py --in obc.sqlite --out obc-defs.sqlite
"""

import argparse
import re
import sqlite3
import sys
import unicodedata

# The Code and the Act use different conventions and both must be matched.
#
#   Division B / Division A:  Absorption trench means an excavation ...
#   Building Code Act, 1992:  "building" means a structure ...
#
# CODE_BOUNDARY requires a non-letter before the capital so a capitalised
# word mid-sentence is not mistaken for a boundary. ACT_BOUNDARY keys on the
# quotation marks, which makes it far less ambiguous - the Act quotes every
# term it defines.
CODE_BOUNDARY = re.compile(
    r"(?<![A-Za-z])"
    # (?!means) stops the term swallowing the definition: "Exit means that
    # part of a means of egress" otherwise captures up to the SECOND "means",
    # yielding the term "Exit means that part of a" and losing "Exit".
    r"([A-Z][A-Za-z0-9\u2019'\-]*(?:[ \-](?!means\b)[A-Za-z0-9\u2019'\-]+){0,5})"
    r"(?:\s*\([^)]{1,40}\))?"       # optional qualifier: (Group A), (Group B, Division 3)
    r"\s+means\b"
)
ACT_BOUNDARY = re.compile(
    r"[\u201c\"]([^\u201d\"]{2,60})[\u201d\"]\s*,?\s*means\b"
)

DEF_PARENT = "A/1/1.4.1.2"
ACT_PARENTS = ("ACT/1/(1)", "ACT/15.1/(1)")
MIN_BLOB = 400          # below this a clause is a real clause, not a blob
MIN_DEF_LEN = 12        # a definition shorter than this is a split artifact


def norm(s):
    """Fold for matching: lowercase, strip accents, collapse whitespace."""
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = s.replace("\u2019", "'").lower()
    return re.sub(r"[\s\-]+", " ", s).strip()


def sortkey(s):
    """Alphabetical key matching how the Code orders its definitions:
    hyphens and spaces are not significant."""
    return re.sub(r"[^a-z0-9]", "", norm(s))


def singulars(s):
    """All plausible singular forms, not the first rule that fires.

    Applying rules in priority order is wrong here: "fixtures" ends in
    "es", so an es->"" rule returns "fixtur" and the real term "fixture"
    is never tried. Multi-word terms are also inflected on the last word
    only ("storage garages" -> "storage garage"), so both the whole
    string and the final word are varied.
    """
    def variants(w):
        out = {w}
        for suf, rep in (("ies", "y"), ("ses", "s"), ("es", ""), ("s", ""), ("es", "e")):
            if w.endswith(suf) and len(w) - len(suf) >= 3:
                out.add(w[: len(w) - len(suf)] + rep)
        return out

    cands = set(variants(s))
    if " " in s:
        head, _, last = s.rpartition(" ")
        cands |= {f"{head} {v}" for v in variants(last)}
    cands.discard(s)
    return cands


def slug(term):
    return re.sub(r"[^a-z0-9]+", "-", norm(term)).strip("-")


def split_blob(node_id, body, style="code"):
    """Return [(term, definition_text, offset)] for one blob, keeping only
    boundaries that preserve alphabetical order.

    The Act's quoted form is unambiguous enough that the alphabetical filter
    is not needed and would wrongly discard terms where the Act departs from
    strict ordering; only the Code's bare form needs it."""
    rx = ACT_BOUNDARY if style == "act" else CODE_BOUNDARY
    hits = [(m.start(), m.group(1), m.end()) for m in rx.finditer(body)]
    if not hits:
        return [], []

    if style == "act":
        out = []
        for k, (start, term, _) in enumerate(hits):
            stop = hits[k + 1][0] if k + 1 < len(hits) else len(body)
            text = body[start:stop].strip()
            if len(text) >= MIN_DEF_LEN:
                out.append((term, text, start))
        return out, []

    # Longest non-decreasing alphabetical subsequence over the boundaries.
    # O(n^2) is fine: the largest blob has a few hundred candidates.
    n = len(hits)
    best = [1] * n
    prev = [-1] * n
    for i in range(n):
        for j in range(i):
            if sortkey(hits[j][1]) <= sortkey(hits[i][1]) and best[j] + 1 > best[i]:
                best[i], prev[i] = best[j] + 1, j
    end = max(range(n), key=lambda i: best[i])
    keep = []
    while end != -1:
        keep.append(end)
        end = prev[end]
    keep.reverse()
    rejected = [hits[i][1] for i in range(n) if i not in set(keep)]

    out = []
    for k, idx in enumerate(keep):
        start, term, _ = hits[idx]
        stop = hits[keep[k + 1]][0] if k + 1 < len(keep) else len(body)
        text = body[start:stop].strip()
        if len(text) >= MIN_DEF_LEN:
            out.append((term, text, start))

    # Second pass. The alphabetical filter is conservative by design and will
    # reject a real boundary whenever a spurious hit sits between two real
    # ones, silently merging two definitions into one node. Re-split any
    # result that still contains a boundary, but only where that boundary
    # follows a sentence end - which is how consecutive definitions are
    # joined, and which a mid-definition "... X means ..." never satisfies.
    final = []
    for term, text, start in out:
        inner = [m for m in rx.finditer(text)
                 if m.start() > 0 and re.search(r"[.;)]\s+$", text[max(0, m.start() - 6):m.start()])]
        if not inner:
            final.append((term, text, start))
            continue
        cuts = [0] + [m.start() for m in inner] + [len(text)]
        names = [term] + [m.group(1) for m in inner]
        for i, nm in enumerate(names):
            piece = text[cuts[i]:cuts[i + 1]].strip()
            if len(piece) >= MIN_DEF_LEN:
                final.append((nm, piece, start + cuts[i]))
        rejected = [r for r in rejected if r not in names]
    return final, rejected


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", default="obc.sqlite")
    ap.add_argument("--out", dest="dst", default="obc-defs.sqlite")
    ap.add_argument("--verbose", action="store_true")
    a = ap.parse_args()

    import shutil
    shutil.copyfile(a.src, a.dst)
    c = sqlite3.connect(a.dst)
    c.row_factory = sqlite3.Row

    def subtree_body(node_id):
        """Concatenated text of a node and its descendants, in document
        order. The Act's definition of 'building' has a 30-character body
        ('In this Act, "building" means,') with the substance in child
        subclauses, so splitting the body alone finds nothing."""
        rows = c.execute(
            """SELECT n.body FROM closure cl JOIN node n ON n.id = cl.descendant
               WHERE cl.ancestor = ? ORDER BY cl.depth, n.page, n.rowid""",
            (node_id,)).fetchall()
        return " ".join((r["body"] or "").strip() for r in rows if (r["body"] or "").strip())

    targets = []
    for r in c.execute(
        """SELECT id, permalink, volume, type, number, designator, body, parent, depth, page
           FROM node WHERE (id = ? OR id LIKE ?) AND body IS NOT NULL
           AND length(body) >= ? ORDER BY id""",
            (DEF_PARENT, DEF_PARENT + "/%", MIN_BLOB)):
        targets.append((dict(r), r["body"], "code"))

    for p in ACT_PARENTS:
        for r in c.execute(
            """SELECT id, permalink, volume, type, number, designator, body, parent, depth, page
               FROM node WHERE id = ? OR id LIKE ? ORDER BY id""", (p, p + "/%")):
            text = subtree_body(r["id"])
            if len(text) >= MIN_BLOB and ACT_BOUNDARY.search(text):
                targets.append((dict(r), text, "act"))

    # A parent and its child can both qualify; keep the outermost so the
    # same definition is not emitted twice.
    # Only act blobs can nest: their text is the subtree, so a child would
    # duplicate its parent. Code blobs use their own body, which does not
    # include the children's, so siblings and children are all distinct.
    act_ids = [o["id"] for o, _, st in targets if st == "act"]
    keep = []
    for row, text, style in targets:
        if style == "act" and any(row["id"] != a and row["id"].startswith(a + "/")
                                  for a in act_ids):
            continue
        keep.append((row, text, style))
    targets = keep

    print(f"definition blobs found: {len(targets)}")
    defs, rejects = [], []
    for b, text, style in targets:
        got, rej = split_blob(b["id"], text, style)
        rejects += [(b["id"], r) for r in rej]
        print(f"  [{style}] {b['id']:<26} {len(text):>6} chars -> "
              f"{len(got):>3} definitions ({len(rej)} rejected)")
        for term, dtext, off in got:
            defs.append(dict(term=term, text=dtext, offset=off, blob=b["id"],
                             volume=b["volume"], page=b["page"],
                             depth=(b["depth"] or 0) + 1))

    if not defs:
        sys.exit("no definitions extracted - check BOUNDARY against the source")

    # Emit defined_term nodes. Duplicate slugs get a numeric suffix so the
    # primary key stays honest rather than silently collapsing two terms.
    c.execute("""CREATE TABLE IF NOT EXISTS definition (
                   id TEXT PRIMARY KEY, term TEXT NOT NULL, norm TEXT NOT NULL,
                   blob TEXT NOT NULL, offset INTEGER, body TEXT NOT NULL)""")
    c.execute("CREATE INDEX IF NOT EXISTS definition_norm ON definition(norm)")

    seen, inserted = {}, 0
    for d in defs:
        base = f"DEF/{slug(d['term'])}"
        nid = base
        if nid in seen:
            seen[base] += 1
            nid = f"{base}~{seen[base]}"
        else:
            seen[base] = 0
        c.execute(
            """INSERT INTO node (id, permalink, volume, type, number, designator,
                                 heading, body, parent, depth, page, bbox)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (nid, nid, d["volume"], "defined_term", None, None,
             d["term"], d["text"], d["blob"], d["depth"], d["page"], None))
        c.execute("INSERT INTO definition (id, term, norm, blob, offset, body) "
                  "VALUES (?,?,?,?,?,?)",
                  (nid, d["term"], norm(d["term"]), d["blob"], d["offset"], d["text"]))
        c.execute("INSERT INTO closure (ancestor, descendant, depth) VALUES (?,?,0)", (nid, nid))
        for anc in c.execute("SELECT ancestor, depth FROM closure WHERE descendant = ?",
                             (d["blob"],)).fetchall():
            c.execute("INSERT OR IGNORE INTO closure (ancestor, descendant, depth) "
                      "VALUES (?,?,?)", (anc["ancestor"], nid, anc["depth"] + 1))
        inserted += 1

    print(f"\ndefined_term nodes inserted: {inserted}")

    # Rewire term edges. Exact normalised match, then singularised match.
    lookup = {}
    for r in c.execute("SELECT id, norm FROM definition"):
        lookup.setdefault(r["norm"], r["id"])
    for k in list(lookup):
        for v in singulars(k):
            lookup.setdefault(v, lookup[k])

    c.execute("""CREATE TABLE IF NOT EXISTS term_resolved (
                   src TEXT NOT NULL, dst TEXT NOT NULL, term TEXT NOT NULL,
                   blob TEXT, how TEXT)""")
    c.execute("CREATE INDEX IF NOT EXISTS term_resolved_src ON term_resolved(src)")
    c.execute("CREATE INDEX IF NOT EXISTS term_resolved_dst ON term_resolved(dst)")

    hit_exact = hit_sing = miss = 0
    missed_terms = set()
    for r in c.execute("SELECT src, dst, term FROM term").fetchall():
        n = norm(r["term"])
        tgt, how = lookup.get(n), "exact"
        if tgt is None:
            how = "singular"
            for v in singulars(n):
                tgt = lookup.get(v)
                if tgt:
                    break
        if tgt is None:
            miss += 1
            missed_terms.add(r["term"])
            continue
        hit_exact += how == "exact"
        hit_sing += how == "singular"
        c.execute("INSERT INTO term_resolved (src, dst, term, blob, how) VALUES (?,?,?,?,?)",
                  (r["src"], tgt, r["term"], r["dst"], how))

    tot = hit_exact + hit_sing + miss
    c.commit()

    print(f"\nterm edges rewired: {hit_exact + hit_sing}/{tot} "
          f"({100*(hit_exact+hit_sing)/max(1,tot):.2f}%)")
    print(f"  exact match:    {hit_exact}")
    print(f"  singular match: {hit_sing}")
    print(f"  unmatched:      {miss} ({len(missed_terms)} distinct)")
    if missed_terms and a.verbose:
        print("  unmatched terms:", ", ".join(sorted(missed_terms)[:40]))
    if rejects and a.verbose:
        print("  rejected boundaries:", ", ".join(t for _, t in rejects[:40]))

    before = c.execute("SELECT COUNT(DISTINCT dst) FROM term").fetchone()[0]
    after = c.execute("SELECT COUNT(DISTINCT dst) FROM term_resolved").fetchone()[0]
    print(f"\ndistinct definition targets: {before} -> {after}")
    med = c.execute("""SELECT AVG(n) FROM (SELECT length(body) n FROM node
                       WHERE type='defined_term')""").fetchone()[0]
    print(f"mean definition length: {med:.0f} chars "
          f"(was 16,930 across the six blobs)")
    print("\nRESULT: PASS" if miss == 0 else f"\nRESULT: PARTIAL ({miss} unmatched)")


if __name__ == "__main__":
    main()
