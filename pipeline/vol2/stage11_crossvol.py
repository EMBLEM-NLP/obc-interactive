#!/usr/bin/env python3
"""Stage 11 - re-resolve Volume 1's external references against the merged model.

Volume 1 held 1,054 citations whose targets were not in the file: Note A-x,
Supplementary Standards, Forms. With Volume 2 merged they have somewhere to go.
"""
import gzip, json, re, time
from collections import Counter

nodes, order, meta = {}, [], None
for line in gzip.open("out/docgraph-merged.jsonl.gz", "rt"):
    r = json.loads(line)
    if r.get("_meta"):
        meta = r
    else:
        nodes[r["id"]] = r
        order.append(r["id"])

notes = {}
for nid, n in nodes.items():
    if n["type"] == "note" and n["number"]:
        notes[re.sub(r"[.\s]", "", n["number"]).upper()] = nid
stds = {n["number"]: nid for nid, n in nodes.items()
        if n["type"] == "supplementary_standard" and n["number"]}
print(f"index: notes {len(notes)} | supplementary standards {len(stds)}")

NOTE = re.compile(r"^A-(.+)$")
SUPP = re.compile(r"^(S[ABC]-\d+)$")
t0 = time.time()
stat = Counter()
for nid, n in nodes.items():
    if n.get("volume") != 1:
        continue
    for r in n.get("refs", []):
        if r.get("target"):
            continue
        why = r.get("why") or ""
        if r["kind"] == "note":
            raw = r["text"].replace("Note", "").strip().strip("().,;")
            m = re.match(r"A-([\d.]+)((?:\(\w+\))*)", raw)
            hit = None
            if m:
                # walk up by NUMBER COMPONENT, not by character: a note cited at
                # sentence level lives under its article in Appendix A
                comps = [c for c in m.group(1).split(".") if c]
                tail = m.group(2)
                keys = sorted(notes)
                for k in range(len(comps), 0, -1):
                    stem = "A-" + "".join(comps[:k])
                    exact = stem + re.sub(r"[.\s]", "", tail if k == len(comps) else "")
                    hit = notes.get(exact.upper()) or notes.get(stem.upper())
                    if hit:
                        break
                    # a citation truncated at "(1" or given at article level still
                    # names a note that exists only at sentence level
                    pref = [x for x in keys if x.startswith(stem.upper())]
                    if len(pref) == 1:
                        hit = notes[pref[0]]
                        break
                    if pref and k == len(comps):
                        hit = notes[min(pref, key=len)]
                        break
            if hit:
                r["target"] = hit; r["why"] = "resolved in Volume 2"
                stat["note -> Appendix A"] += 1
            else:
                stat["note still unresolved"] += 1
        elif r["kind"] == "supp":
            m = SUPP.match(r["text"].strip())
            hit = stds.get(m.group(1)) if m else None
            if hit:
                r["target"] = hit; r["why"] = "resolved in Volume 2"
                stat["supplementary standard"] += 1
            else:
                stat["supp still unresolved"] += 1
        elif r["kind"] == "form":
            stat["form (Volume 2 Forms section, not yet keyed)"] += 1

with gzip.open("out/docgraph-merged.jsonl.gz", "wt", encoding="utf-8") as fh:
    fh.write(json.dumps({**meta}) + "\n")
    for nid in order:
        fh.write(json.dumps(nodes[nid], ensure_ascii=False) + "\n")
for k, v in stat.most_common():
    print(f"   {v:>5}  {k}")
print(f"{time.time()-t0:.0f}s")
