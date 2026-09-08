#!/usr/bin/env python3
"""Stage 7 - citation grammar and resolver.

ONE grammar, ONE resolver, applied to node text and table-cell text through the
same code path. Every citation resolves to a node id or carries a reason code.
Nothing is silently dropped, so the question stops being "did I think of this
pattern?" and becomes "does the grammar cover this form?"
"""
import gzip, json, re, time
from collections import Counter, defaultdict

nodes, order, meta = {}, [], None
for line in gzip.open("out/docgraph.jsonl.gz", "rt"):
    r = json.loads(line)
    if r.get("_meta"):
        meta = r
    else:
        nodes[r["id"]] = r
        order.append(r["id"])

# ---------------- indexes built from the graph itself ----------------
by_num = defaultdict(dict)          # division -> number -> id
tables = defaultdict(dict)          # division -> designator -> id
act = {}                            # section number -> id
for nid, n in nodes.items():
    if n["type"] in ("section", "subsection", "article") and n["number"]:
        d = nid.split("/")[0]
        by_num[d][n["number"]] = nid
    elif n["type"] == "table" and n["number"]:
        by_num_key = nid.split("/")[0]
        tables[by_num_key][n["number"].rstrip(".")] = nid
    elif n["type"] == "act_section" and n["number"]:
        act[n["number"]] = nid

# defined terms: "Term means ..." inside Division A 1.4.1.x
# a definition's home is the LINE that defines it, not the clause node it sits in:
# Article 1.4.1.2 is one sentence whose clauses run for 24 pages, so the node's
# own provenance points at where the clause began, not at the term.
terms = {}
for nid, n in nodes.items():
    if not (nid.startswith("A/1/1.4.1") or nid.startswith("ACT/")):
        continue
    for t in n["text"]:
        m = re.match(r"^[“\"]?(.{2,60}?)[”\"]?\s+means\b", t["t"])
        if m:
            key = re.sub(r"\s*\(.*?\)\s*$", "", m.group(1)).strip().lower().strip("“”\"")
            terms.setdefault(key, {"node": nid, "page": t["p"],
                                   "y": (t.get("b") or [0, 60])[1]})

# referenced standards: the Referenced Documents table is now a real grid
std = {}
for nid, n in nodes.items():
    if n.get("type") != "table" or not n["number"].startswith("1.3.1.2"):
        continue
    for c in n["grid"]:
        for tok in c["text"].split():
            tok = tok.strip(".,;“”\"")
            if len(tok) > 2 and any(ch.isdigit() for ch in tok):
                std.setdefault(tok, nid)
std_keys = sorted(std)

def normdes(x):
    return re.sub(r"[.\-\s]", "", x).upper()
tables_norm = defaultdict(dict)
for dd, m in tables.items():
    for des, tid in m.items():
        tables_norm[dd][normdes(des)] = tid

# ---------------- the grammar ----------------
G = {
 "code_ref":  r"(?P<code>\d+(?:\.\d+){1,4}[A-Z]?)\.(?:\((?P<sent>\d+(?:\.\d+)?)\))?(?:\((?P<cl>[a-z])\))?",
 "cap_ref":   r"(?P<capkind>Table|Figure)\s+(?P<cap>[A-Z]?-?\d+(?:\.\d+){1,4}\.?(?:-[A-Z0-9/]+)?)",
 "act_ref":   r"\b(?:section|subsection|clause)s?\s+(?P<act>\d+(?:\.\d+){0,2})(?:\((?P<asub>\d+(?:\.\d+)?)\))?(?:\((?P<acl>[a-z](?:\.\d+)?)\))?",
 "short":     r"\b(?P<sk>ss?)\.\s*(?P<sn>\d+(?:\.\d+)?)",
 "note":      r"\bNote\s+(?P<note>A-\d+(?:\.\d+)*[^\s,;)]*)",
 "supp":      r"\b(?P<supp>S[ABC]-\d+)\b",
 "form":      r"\bForm\s+(?P<form>\d+(?:\.\d+){1,4}\.?-[A-Z])",
 "ca":        r"\bC\.A\.\s*(?P<ca>[A-F]\d{1,3})",
 "std":       r"\b(?P<org>(?:[A-Z]{2,6}/)?(?:CSA|ASTM|ASHRAE|ANSI|ULC|NFPA|ISO|AAMA|ACI|AWWA|CGSB|NSF|AWS|BNQ|AISI|AISC|SMACNA|HVI|MSS|WDMA|APA|ASME|ASSE|CAN))[\s/\-]+(?P<des>[A-Z]{0,6}[\d][\w./\-]*)",
}
# \b matters: without it "section" matches inside "Subsection 3.2.6.",
# turning 500 Code citations into phantom Act references.
# code_ref before act_ref: a Code citation always ends the number with a period
# ("Subsection 3.2.6. of Division B"), an Act citation never does ("subsection 34(2.3)")
ORDER = ["cap_ref", "note", "supp", "form", "ca", "std", "code_ref", "act_ref", "short"]
RX = re.compile("|".join(f"(?P<{k}__>{G[k]})" for k in ORDER))
DIVQ = re.compile(r"\s*of\s+Division\s+([ABC])")
ACTQ = re.compile(r"\s*of\s+(?:this|the)\s+Act\b", re.I)
OTHERACT = re.compile(r"of the [A-Z][\w ]+ Act")

def resolve_code(num, d, tail):
    m = DIVQ.match(tail)
    if m:
        d = m.group(1)
    exact = by_num[d].get(num)
    if exact:
        return exact, "exact"
    for dd in ("B", "A", "C"):
        if dd != d and num in by_num[dd]:
            return by_num[dd][num], "other-division"
    parts = num.rstrip(".").split(".")
    for n in range(len(parts) - 1, 1, -1):
        anc = ".".join(parts[:n])
        if anc in by_num[d]:
            return by_num[d][anc], "ancestor"
    return None, "not-in-this-edition"

std_norm = {}
for k, v in std.items():
    std_norm.setdefault(normdes(k), v)

def find_std(des, full=None):
    for cand in ([full, des] if full else [des]):
        if cand in std:
            return std[cand]
        if normdes(cand) in std_norm:
            return std_norm[normdes(cand)]
        hit = [k for k in std_keys if normdes(k).startswith(normdes(cand))]
        if len(hit) == 1:
            return std[hit[0]]
    return None

t0 = time.time()
stat = Counter()
spans_added = 0
for nid, n in nodes.items():
    d = nid.split("/")[0]
    if d not in ("A", "B", "C"):
        d = "B"
    joined, omap = "", []          # omap: (start, end, line index)
    for i, tt in enumerate(n["text"]):
        if joined:
            joined += " "
        omap.append((len(joined), len(joined) + len(tt["t"]), i))
        joined += tt["t"]
    chunks = [("*", joined)] if joined else []
    if n.get("grid"):
        chunks += [(f"g{i}", c["text"]) for i, c in enumerate(n["grid"])]
    refs = []
    for idx, text in chunks:
        if not text:
            continue
        for m in RX.finditer(text):
            tail = text[m.end():m.end() + 22]
            kind = next(k for k in ORDER if m.group(k + "__"))
            tgt, why = None, None
            if kind == "code_ref":
                if m.start() and text[m.start() - 1].isalpha():
                    stat["skipped: standard designation, not a clause"] += 1
                    continue
                if OTHERACT.search(tail):
                    stat["skipped: another statute"] += 1
                    continue
                tgt, why = resolve_code(m.group("code"), d, tail)
                if tgt and m.group("sent") and f'{tgt}/({m.group("sent")})' in nodes:
                    tgt = f'{tgt}/({m.group("sent")})'
                    if m.group("cl") and f'{tgt}/({m.group("cl")})' in nodes:
                        tgt = f'{tgt}/({m.group("cl")})'
            elif kind == "cap_ref":
                dd = DIVQ.match(tail).group(1) if DIVQ.match(tail) else d
                des = normdes(m.group("cap"))
                tgt = tables_norm[dd].get(des) or next(
                    (tables_norm[x].get(des) for x in "BAC" if tables_norm[x].get(des)), None)
                why = "exact" if tgt else "not-in-this-edition"
                if not tgt and m.group("capkind").lower() == "figure":
                    why = "figure asset"
            elif kind == "act_ref":
                if OTHERACT.search(text[max(0, m.start() - 8):m.end() + 60]):
                    stat["skipped: another statute"] += 1
                    continue
                tgt = act.get(m.group("act"))
                # now that the Act is a tree, land on the subsection and clause
                if tgt and m.group("asub") and f'{tgt}/({m.group("asub")})' in nodes:
                    tgt = f'{tgt}/({m.group("asub")})'
                    if m.group("acl") and f'{tgt}/({m.group("acl")})' in nodes:
                        tgt = f'{tgt}/({m.group("acl")})'
                why = "exact" if tgt else "not-in-this-edition"
            elif kind == "short":
                if not ACTQ.search(tail) and "this Act" not in tail:
                    stat["skipped: amending-statute citation"] += 1
                    continue
                tgt = act.get(m.group("sn"))
                why = "exact" if tgt else "not-in-this-edition"
            elif kind == "note":
                why = "external: Appendix A (Volume 2)"
            elif kind == "supp":
                why = "external: Supplementary Standard (Volume 2)"
            elif kind == "form":
                why = "external: Forms (Volume 2)"
            elif kind == "ca":
                why = "compliance-alternative row"
            elif kind == "std":
                tgt = find_std(m.group("des").rstrip(".,;"), m.group(0).rstrip(".,;"))
                why = "exact" if tgt else "not-in-Table-1.3.1.2"
            stat[f"{kind}: {'resolved' if tgt else why}"] += 1
            ln = next((i for a, b, i in omap if a <= m.start() < b), None) if idx == "*" else None
            refs.append({"chunk": idx, "line": ln, "s": m.start(), "e": m.end(),
                         "kind": kind, "text": m.group(0), "target": tgt, "why": why})
            spans_added += 1
    if refs:
        n["refs"] = refs

# defined terms from the preserved italic runs
term_hits = 0
for nid, n in nodes.items():
    seen = set()
    tr = []
    for i, t in enumerate(n["text"]):
        for run in t.get("it", []):
            key = re.sub(r"['’]s$", "", run.strip().lower().strip(".,;:()“”\"'’ "))
            if not key or (t["p"], key) in seen:
                continue
            hit = next((terms[c] for c in (key, key.rstrip("s"), key + "s",
                                           re.sub(r"ies$", "y", key)) if c in terms), None)
            # dedupe per PAGE, not per node: a node can run for pages, and one
            # link at its start leaves every later page dead
            pkey = (t["p"], key)
            if hit and hit["node"] != nid and pkey not in seen:
                seen.add(pkey)
                tr.append({"chunk": i, "term": key, "target": hit["node"],
                           "to_page": hit["page"], "to_y": max(40.0, hit["y"] - 6)})
                term_hits += 1
    if tr:
        n["terms"] = tr

with gzip.open("out/docgraph.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({**meta, "nodes": len(nodes)}) + "\n")
    for nid in order:
        fh.write(json.dumps(nodes[nid], ensure_ascii=False) + "\n")

print(f"index: clauses {sum(len(v) for v in by_num.values())} | tables "
      f"{sum(len(v) for v in tables.values())} | act {len(act)} | terms {len(terms)} | standards {len(std)}")
print(f"citations found: {spans_added} | defined-term links: {term_hits} | {time.time()-t0:.0f}s\n")
for k, v in stat.most_common():
    print(f"   {v:>6}  {k}")
