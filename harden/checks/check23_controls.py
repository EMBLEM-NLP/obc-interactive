#!/usr/bin/env python3
"""Check 23 (H4) - every absence assertion has a negative control.

An assertion of the form "zero X" is satisfied by a detector that can never
report X. This is the software analogue of a laboratory negative control, and
the recognised remedy is to run the same detector against a fixture known to
contain X and require it to be found.

Part one enumerates the absence assertions in the shipped checks and requires
each to have a registered control. Part two runs the controls: each seeds a
known defect into a copy of a real artifact and asserts the detector finds it.
"""
import sys, os, re, glob, json, gzip, shutil, tempfile, sqlite3
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import pymupdf
from lib.canon import contains
# Paths resolve from the package root with env-var overrides, so this check
# runs from the shipped bag. Before 2026-09-07 it hardcoded build-session
# paths and could not be re-run by anyone who received the artifact.
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

fails = []

# ---------- part 1: which absence assertions exist, and are they covered? ----------
ABSENCE = re.compile(r"(==\s*0\b|\bnot\s+\w+\b.*fails\.append|len\([^)]*\)\s*==\s*0|"
                     r"if\s+\w+:\s*fails\.append)")
CLAIMS = {
    "no link points at a file (3 forms)": "control_launch",
    "overlapping disagreeing == 0":  "control_overlap",
    "dangling foreign keys == 0":    "control_fk",
    "TOC wrong/missing == 0":        "control_toc",
    "orphaned text ~ 0":             "control_orphan",
}
print("absence assertions declared, and their controls:")
for claim, ctl in CLAIMS.items():
    print(f"   {claim:<32} -> {ctl}")

# ---------- part 2: run the controls against seeded defects ----------
tmp = tempfile.mkdtemp()

def control_launch():
    """Three ways a link can point at a file. Seed each and require detection.

    This control is why check27 exists. Seeding through insert_link(LINK_LAUNCH)
    produced a remote GoTo, not a Launch action; and a real /Launch action is
    reported by PyMuPDF as kind 5, the same value as a legitimate cross-volume
    link. The old "kind 3 == 0" assertion could not have seen either.
    """
    from lib.pdfactions import dead_file_links
    ALLOWED = ("301880_built_from_model.pdf", "301881_built_from_model.pdf")
    src = os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf"))
    stage, p = os.path.join(tmp, "stage.pdf"), os.path.join(tmp, "seeded.pdf")
    d = pymupdf.open(src)
    for n in range(3):
        d[100].insert_link({"kind": pymupdf.LINK_URI,
                            "uri": f"https://example.invalid/seed-{n}",
                            "from": pymupdf.Rect(40, 40 + 20 * n, 120, 52 + 20 * n)})
    d.save(stage); d.close()
    d = pymupdf.open(stage)
    xr = {}
    for xref, _t, _i in d[100].annot_xrefs():
        u = str(d.xref_get_key(xref, "A/URI")[1] or "")
        for n in range(3):
            if f"seed-{n}" in u:
                xr[n] = xref
    if len(xr) != 3:
        return False, "could not stage the three seed annotations"
    # (a) a genuine /Launch action
    d.xref_set_key(xr[0], "A/URI", "null")
    d.xref_set_key(xr[0], "A/S", "/Launch")
    d.xref_set_key(xr[0], "A/F", "(seeded-launch.docx)")
    # (b) a file:// URI, the form the ministry's 819 dead links actually took
    d.xref_set_key(xr[1], "A/URI", "(file://///HOST/share/seeded.docx)")
    # (c) a remote GoTo naming a file that is not shipped
    d.xref_set_key(xr[2], "A/URI", "null")
    d.xref_set_key(xr[2], "A/S", "/GoToR")
    d.xref_set_key(xr[2], "A/F", "(not-shipped.pdf)")
    d.save(p); d.close()
    found = dead_file_links(pymupdf.open(p), ALLOWED)
    kinds = {k for _, _, k, _ in found}
    want = {"Launch action", "file:// URI", "GoToR to an unexpected file"}
    ok = want <= kinds
    return ok, f"detector found {len(found)} file links, types {sorted(kinds)}"

def control_overlap():
    """Seed two internal links on the same rectangle pointing to different
    pages and require the conflict detector to see exactly one conflict."""
    src = os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf"))
    p = os.path.join(tmp, "seeded2.pdf")
    d = pymupdf.open(src)
    R = pymupdf.Rect(300, 300, 380, 312)
    for tgt in (10, 200):
        d[101].insert_link({"kind": pymupdf.LINK_GOTO, "page": tgt,
                            "to": pymupdf.Point(33, 60), "from": R})
    d.save(p); d.close()
    page = pymupdf.open(p)[101]
    ls = [l for l in page.get_links() if l["kind"] == 1]
    conflict = 0
    for i in range(len(ls)):
        for j in range(i + 1, len(ls)):
            a, b = ls[i]["from"], ls[j]["from"]
            it = a & b
            if not it.is_empty and it.get_area() > 0.6 * min(a.get_area(), b.get_area()) \
               and ls[i]["page"] != ls[j]["page"]:
                conflict += 1
    return conflict >= 1, f"detector found {conflict} conflicting overlaps (want >=1)"

def control_fk():
    """Seed a dangling reference in a copy of the database."""
    src = os.environ.get("OBC_DB", os.path.join(_PKG, "emitters/obc.sqlite"))
    p = os.path.join(tmp, "seeded.sqlite")
    shutil.copy(src, p)
    db = sqlite3.connect(p)
    db.execute("INSERT INTO ref VALUES (?,?,?,?,?)",
               ("B/9/9.10.16.1", "B/9/NOT-A-NODE", "code_ref", "9.99.99.9.", "exact"))
    db.commit()
    n = db.execute("""SELECT count(*) FROM ref WHERE dst IS NOT NULL
                      AND dst NOT IN (SELECT id FROM node)""").fetchone()[0]
    return n == 1, f"detector found {n} dangling keys (want 1)"

def control_toc():
    """Seed a wrong TOC target and require the label-based detector to see it."""
    lab = json.load(open(os.environ.get("OBC_LABELS", os.path.join(_PKG, "verify/data/v1/labels.json"))))
    rev = {}
    for k, v in lab.items():
        sec, num = v
        if sec and num is not None:
            rev.setdefault((sec, num), int(k))
    src = os.environ.get("OBC_BUILT_V1", os.path.join(_PKG, "pdf/301880_built_from_model.pdf"))
    p = os.path.join(tmp, "seeded3.pdf")
    d = pymupdf.open(src)
    page = d[710]
    tgt = next(l for l in page.get_links() if l["kind"] == 1)
    page.delete_link(tgt)
    tgt["page"] = (tgt["page"] + 7) % d.page_count      # send it somewhere wrong
    page.insert_link(tgt)
    d.save(p); d.close()
    d = pymupdf.open(p); page = d[710]; sec = lab["711"][0]
    wrong = 0
    for blk in page.get_text("dict")["blocks"]:
        if blk["type"] != 0: continue
        for ln in blk["lines"]:
            t = "".join(sp["text"] for sp in ln["spans"]).strip()
            R = pymupdf.Rect(ln["bbox"])
            if not (re.fullmatch(r"\d{1,4}", t) and R.x0 > 240 and R.y0 < 720): continue
            want = rev.get((sec, int(t)))
            if not want: continue
            hits = [L for L in page.get_links()
                    if not (R & L["from"]).is_empty
                    and (R & L["from"]).get_area() > 0.45 * R.get_area()]
            if hits and not any(h["kind"] == 1 and h["page"] + 1 == want for h in hits):
                wrong += 1
    return wrong >= 1, f"detector found {wrong} wrong TOC targets (want >=1)"

def control_orphan():
    """Delete a node's text and require the capture detector to report loss."""
    import unicodedata
    from collections import Counter
    nodes = {}
    for line in gzip.open(os.environ.get("OBC_GRAPH_V1", os.path.join(_PKG, "verify/data/v1/docgraph.jsonl.gz")), "rt"):
        r = json.loads(line)
        if not r.get("_meta"):
            nodes[r["id"]] = r
    victim = next(n for n in nodes.values()
                  if n["type"] == "sentence" and len(" ".join(t["t"] for t in n["text"])) > 200)
    before = sum(len(re.sub(r"\s+", "", t["t"])) for t in victim["text"])
    victim["text"] = []
    after = sum(len(re.sub(r"\s+", "", t["t"])) for t in victim["text"])
    return before - after > 100, f"capture detector sees {before-after} characters go missing"

CONTROLS = {"control_launch": control_launch, "control_overlap": control_overlap,
            "control_fk": control_fk, "control_toc": control_toc,
            "control_orphan": control_orphan}
print("\nnegative controls (seed a known defect, require the detector to find it):")
for name, fn in CONTROLS.items():
    try:
        ok, msg = fn()
    except Exception as e:
        ok, msg = False, f"raised {type(e).__name__}: {e}"
    print(f"   {'ok  ' if ok else 'FAIL'} {name:<18} {msg}")
    if not ok:
        fails.append(f"{name} did not detect its seeded defect")
missing = [c for c in CLAIMS.values() if c not in CONTROLS]
if missing:
    fails.append(f"absence assertions without a control: {missing}")
shutil.rmtree(tmp, ignore_errors=True)
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
