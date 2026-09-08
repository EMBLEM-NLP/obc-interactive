#!/usr/bin/env python3
"""Check 26 (H8) - machine-readable provenance and a check-results attestation.

Two recognised formats, both generated from the artifacts:

  * RO-Crate 1.1 - expresses the derivation graph (source PDFs -> document graph
    -> the four derived formats) as CreateAction entities, which is what a
    reviewer needs to see to call an artifact reusable.
  * in-toto Statement v1 - the correct format for "these checks passed on these
    artifacts": each subject is named by digest, the predicate records the gate,
    its command, its expectation and its result.

Signing is out of scope here (no key material, no network), so the statement is
emitted unsigned and the check says so rather than implying a signature exists.
"""
import sys, os, json, hashlib, glob
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PKG = os.environ.get("OBC_PKG", _PKG)
fails = []

crate = os.path.join(PKG, "ro-crate-metadata.json")
att = os.path.join(PKG, "attestation.intoto.jsonl")
for p, name in ((crate, "RO-Crate metadata"), (att, "in-toto attestation")):
    if not os.path.exists(p):
        fails.append(f"{name} missing")
if fails:
    print("RESULT: FAIL", fails); sys.exit(1)

c = json.load(open(crate))
ctx = c.get("@context")
ok_ctx = "w3id.org/ro/crate/1.1" in json.dumps(ctx)
ids = {e["@id"]: e for e in c["@graph"]}
actions = [e for e in c["@graph"] if e.get("@type") == "CreateAction"]
print(f"RO-Crate context 1.1     : {ok_ctx}")
print(f"entities                 : {len(c['@graph'])}")
print(f"derivation actions       : {len(actions)}")
for a in actions:
    obj = a.get("object"); res = a.get("result")
    print(f"   {a.get('name','?')[:44]:<46} object->result")
    for ref in (obj if isinstance(obj, list) else [obj]) + \
               (res if isinstance(res, list) else [res]):
        if isinstance(ref, dict) and ref.get("@id") not in ids:
            fails.append(f"RO-Crate action references an unknown entity {ref.get('@id')}")
if not ok_ctx: fails.append("RO-Crate context is not 1.1")
if len(actions) < 3: fails.append("derivation graph is incomplete")

stmts = [json.loads(l) for l in open(att) if l.strip()]
print(f"in-toto statements       : {len(stmts)}")
bad = 0
for s in stmts:
    if s.get("_type") != "https://in-toto.io/Statement/v1":
        bad += 1; continue
    for subj in s.get("subject", []):
        d = subj.get("digest", {}).get("sha256")
        p = os.path.join(PKG, subj["name"])
        if not d or not os.path.exists(p):
            bad += 1; continue
        real = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if real != d:
            bad += 1
print(f"statements whose subject digest matches the shipped file: {len(stmts)-bad}/{len(stmts)}")
if bad: fails.append(f"{bad} attestation subjects do not match the artifacts")
signed = any("signatures" in s for s in stmts)
print(f"signed                   : {signed} (unsigned by design - no key material here)")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
