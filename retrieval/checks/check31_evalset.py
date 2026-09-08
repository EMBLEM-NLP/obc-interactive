#!/usr/bin/env python3
"""Check 31 (R2) - the evaluation set is real, provenanced and honest.

An eval set generated from the answers measures nothing. This asserts:
  * every target id exists and is an article node
  * the paraphrase subset shares NO content word with its target's own text -
    mechanically enforced, so the hard subset cannot be quietly softened
  * the set is not rigged: a majority of questions DO overlap lexically, so
    FTS5 is given every advantage
  * provenance and limitations are stated in the file itself
"""
import sys, os, json, re, sqlite3
DB = os.environ.get("OBC_DB", "out/obc-vec.sqlite")
ES = os.environ.get("OBC_EVAL", "evalset.json")
STOP = set("a an the of to in on for and or with is are be by at from as that this "
           "it its do does i my what how much when where which who need needs "
           "must should can may shall not no if there their them then than into "
           "out up down over under between about".split())
def words(s):
    return {w for w in re.findall(r"[a-z]+", s.lower()) if w not in STOP and len(w) > 2}
d = json.load(open(ES))
db = sqlite3.connect(DB)
fails = []
qs = d["questions"]
print(f"questions: {len(qs)}  ({sum(1 for q in qs if q['kind']=='paraphrase')} paraphrase, "
      f"{sum(1 for q in qs if q['kind']=='lexical')} lexical)")
for k in ("provenance", "author", "limitations"):
    if not d.get(k): fails.append(f"eval set does not state its {k}")

bad_target, leaky = [], []
for q in qs:
    row = db.execute("SELECT type FROM node WHERE id=?", (q["target"],)).fetchone()
    if not row or row[0] != "article":
        bad_target.append(q["target"]); continue
    txt = " ".join(r[0] or "" for r in db.execute("""
        SELECT n.body FROM closure c JOIN node n ON n.id=c.descendant
        WHERE c.ancestor=?""", (q["target"],)))
    head = db.execute("SELECT coalesce(heading,'') FROM node WHERE id=?",
                      (q["target"],)).fetchone()[0]
    overlap = words(q["q"]) & words(txt + " " + head)
    q["_overlap"] = sorted(overlap)
    if q["kind"] == "paraphrase" and overlap:
        leaky.append((q["q"], sorted(overlap)))
print(f"targets that are not article nodes: {len(bad_target)} {bad_target[:3]}")
if bad_target: fails.append(f"{len(bad_target)} bad targets")
print(f"paraphrase questions leaking a content word: {len(leaky)}")
for q, o in leaky[:5]:
    print(f"   {q[:52]!r} shares {o}")
if leaky: fails.append(f"{len(leaky)} paraphrase questions are not lexically disjoint")
# Gate on the overlap this check MEASURED, not on the hand-written `kind`
# label. As originally written, a question labelled "lexical" with zero real
# overlap still counted as lexical, so replacing 70% of question texts with
# nonsense left the ratio at 82% - the H10 control proved the gate could not
# fail. The label is still checked for consistency below.
lex = [q for q in qs if q["_overlap"]]
mislabelled = [q["q"] for q in qs if q["kind"] == "lexical" and not q["_overlap"]]
if mislabelled:
    fails.append(f"{len(mislabelled)} questions labelled lexical share no content word with their target")
frac = len(lex) / len(qs)
print(f"share of questions that DO overlap lexically: {frac:.0%} "
      f"(the set favours FTS5, not embeddings)")
if frac < 0.5: fails.append("eval set is weighted toward embeddings")
if len(qs) < 40: fails.append("eval set is too small to mean anything")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
