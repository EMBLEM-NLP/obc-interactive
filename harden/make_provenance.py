#!/usr/bin/env python3
"""Emit RO-Crate 1.1 provenance and in-toto v1 check-result statements."""
import json, os, hashlib, sys, subprocess, glob, datetime
PKG = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/package/obc-interactive"
def dig(rel):
    p = os.path.join(PKG, rel)
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None
NOW = "2025-01-17T00:00:00Z"      # from SOURCE_DATE_EPOCH, not the clock
SRC = [{"@id": "https://www.publications.gov.on.ca/store/20170501121/Free_Download_Files/301880.pdf"},
       {"@id": "https://www.publications.gov.on.ca/store/20170501121/Free_Download_Files/301881.pdf"}]
DERIVED = ["model/docgraph-merged.jsonl.gz", "pdf/301880_built_from_model.pdf",
           "pdf/301881_built_from_model.pdf", "emitters/obc.sqlite",
           "emitters/markdown.tar.gz", "emitters/html.tar.gz",
           "emitters/obc-mod.sqlite"]
# NOTE: emitters/obc-vec.sqlite (stage19_embed.py's output) was never added to
# this list when the retrieval layer was introduced, so it - and the R1-R5
# ledger in gates/GATES-retrieval.md - has no in-toto statement or RO-Crate
# entity to this day. Not fixed here: this pass covers the remediation layer
# this integration adds, not a pre-existing gap it did not create.
graph = [
 {"@id": "ro-crate-metadata.json", "@type": "CreativeWork",
  "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"}, "about": {"@id": "./"}},
 {"@id": "./", "@type": "Dataset",
  "name": "2024 Building Code Compendium - unofficial interactive edition",
  "description": "Derived from Publications Ontario 301880 and 301881. "
                 "Current to 2025-01-16 (through O. Reg. 5/25). Not the official version.",
  "datePublished": NOW,
  "license": {"@id": "https://www.ontario.ca/page/copyright-information"},
  "hasPart": [{"@id": p} for p in DERIVED]},
]
for u in SRC:
    graph.append({"@id": u["@id"], "@type": "File", "encodingFormat": "application/pdf",
                  "name": os.path.basename(u["@id"]),
                  "description": "Crown-copyright source, not redistributed; "
                                 "recorded in fetch.txt with its checksum"})
for p in DERIVED:
    d = dig(p)
    graph.append({"@id": p, "@type": "File", "name": os.path.basename(p),
                  "sha256": d, "contentSize": os.path.getsize(os.path.join(PKG, p))})
TOOLS = [("stage0-9 pipeline", "pipeline/run.sh", SRC, ["model/docgraph-merged.jsonl.gz"]),
         ("stage8 link emitter and injector", "pipeline/stage8b_inject.py",
          [{"@id": "model/docgraph-merged.jsonl.gz"}],
          ["pdf/301880_built_from_model.pdf", "pdf/301881_built_from_model.pdf"]),
         ("emitters (sqlite, markdown, html)", "pipeline/emitters/stage15_sqlite.py",
          [{"@id": "model/docgraph-merged.jsonl.gz"}],
          ["emitters/obc.sqlite", "emitters/markdown.tar.gz", "emitters/html.tar.gz"]),
         ("retrieval remediation (definitions, modality)", "retrieval/run.sh",
          [{"@id": "emitters/obc.sqlite"}],
          ["emitters/obc-mod.sqlite"])]
for i, (name, tool, obj, res) in enumerate(TOOLS, 1):
    graph.append({"@id": tool, "@type": "SoftwareApplication", "name": name})
    graph.append({"@id": f"#action-{i}", "@type": "CreateAction", "name": name,
                  "instrument": {"@id": tool},
                  "object": obj, "result": [{"@id": r} for r in res],
                  "endTime": NOW})
json.dump({"@context": "https://w3id.org/ro/crate/1.1/context", "@graph": graph},
          open(os.path.join(PKG, "ro-crate-metadata.json"), "w"), indent=1)

# in-toto: one statement per ledger, subjects named by digest
led = {"volume1": "gates/GATES-volume1.md", "volume2": "gates/GATES-volume2.md",
       "emitters": "gates/GATES-emitters.md", "hardening": "gates/GATES-hardening.md",
       "remediation": "gates/GATES-remediation.md"}
subj_for = {"volume1": ["pdf/301880_built_from_model.pdf"],
            "volume2": ["pdf/301881_built_from_model.pdf"],
            "emitters": ["emitters/obc.sqlite"],
            "hardening": ["model/docgraph-merged.jsonl.gz"],
            "remediation": ["emitters/obc-mod.sqlite"]}
lines = []
for scope, path in led.items():
    full = os.path.join(PKG, path)
    if not os.path.exists(full):
        continue
    txt = open(full, encoding="utf-8").read()
    gates = []
    for m in __import__("re").finditer(r"- \[(x| )\] (\w+): ([^\n]+)", txt):
        gates.append({"id": m.group(2), "met": m.group(1) == "x",
                      "statement": m.group(3).strip()})
    abandoned = [l.split(":", 1)[1].strip()[:120]
                 for l in txt.splitlines() if l.startswith("ABANDON:")]
    lines.append(json.dumps({
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [{"name": s, "digest": {"sha256": dig(s)}}
                    for s in subj_for[scope] if dig(s)],
        "predicateType": "https://obc.example/checks/v1",
        "predicate": {"ledger": path, "gates": gates,
                      "met": sum(g["met"] for g in gates), "total": len(gates),
                      "abandoned": abandoned, "verifiedAt": NOW,
                      "note": "unsigned; sign with cosign sign-blob for tamper evidence"},
    }))
open(os.path.join(PKG, "attestation.intoto.jsonl"), "w").write("\n".join(lines) + "\n")
print(f"ro-crate: {len(graph)} entities | attestation: {len(lines)} statements")
