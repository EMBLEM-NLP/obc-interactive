#!/usr/bin/env python3
"""Check 21 (H2) - the package is a valid BagIt bag.

BagIt (RFC 8493, Library of Congress / CDL) is the recognised format for exactly
this shape of problem: a payload with a checksum manifest, tag files that are
themselves checksummed, and fetch.txt for payload files that are recorded by
checksum but held externally. That last part is what the two Crown-copyright
source PDFs need - they cannot be redistributed, but a third party who obtains
them legally can have byte-identity confirmed.

This replaces the hand-rolled verify/ layout, the symlink materialisation and
the environment-variable source handling.
"""
import sys, os, json, hashlib
import bagit
_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

BAG = os.environ.get("OBC_BAG", os.path.join(_PKG, "..", "bag"))
fails = []
if not os.path.isdir(BAG):
    print("RESULT: FAIL bag not built"); sys.exit(1)
bag = bagit.Bag(BAG)
print(f"bagit version      : {bag.tags.get('BagIt-Version')}")
print(f"payload files      : {len(list(bag.payload_files()))}")
print(f"manifest algorithms: {sorted(bag.algorithms)}")
print(f"has tagmanifest    : {bool(list(bag.tagmanifest_files()))}")

# 1. complete + valid, in RFC 8493's sense
try:
    bag.validate(fast=False, completeness_only=False)
    print("validation         : valid (all payload checksums verify)")
except bagit.BagValidationError as e:
    msgs = [str(d) for d in getattr(e, "details", [])][:4]
    # RFC 8493: a bag with fetch.txt entries is INCOMPLETE until fetched, and
    # that is the expected state here - the source PDFs cannot be redistributed
    fetched = {e[2] for e in [l.split() for l in open(os.path.join(BAG,"fetch.txt"))] if len(e)==3} \
        if os.path.exists(os.path.join(BAG,"fetch.txt")) else set()
    all_msgs = [str(d) for d in getattr(e, "details", [])]
    missing_only = bool(all_msgs) and all(
        any(f in m for f in fetched) and "not found on filesystem" in m for m in all_msgs)
    if missing_only:
        print(f"validation         : incomplete as expected - "
              f"{len(getattr(e,'details',[]))} fetch.txt payloads not present")
    else:
        print(f"validation         : FAILED {msgs}")
        fails.append(f"bag invalid: {msgs}")

# 2. fetch.txt must carry the inputs that cannot be redistributed
fetch = os.path.join(BAG, "fetch.txt")
entries = []
if os.path.exists(fetch):
    for line in open(fetch):
        parts = line.split()
        if len(parts) == 3:
            entries.append(parts)
print(f"fetch.txt entries  : {len(entries)}")
for url, size, path in entries:
    print(f"   {os.path.basename(path):<34} {size:>10}  {url[:52]}")
if len(entries) < 2:
    fails.append("the two source PDFs are not recorded in fetch.txt")

# 3. every fetch.txt payload must ALSO be in the payload manifest by checksum,
#    otherwise the bag records where to get the file but not what it should be
man = {}          # (path, algorithm) -> checksum, kept per-algorithm
for alg in bag.algorithms:
    p = os.path.join(BAG, f"manifest-{alg}.txt")
    if os.path.exists(p):
        for line in open(p):
            h, rel = line.split(None, 1)
            man[(rel.strip(), alg)] = h
unhashed = [e[2] for e in entries if (e[2], "sha512") not in man]
print(f"fetch entries without a checksum: {len(unhashed)} {unhashed}")
if unhashed:
    fails.append("a fetch.txt payload has no manifest checksum")

# 4. the tag files must themselves be checksummed
if not list(bag.tagmanifest_files()):
    fails.append("no tagmanifest - the verification metadata is not self-verifying")

# 5. the recorded checksums must match the real source PDFs when present
for url, size, rel in entries:
    real = os.environ.get("OBC_SRC_V1" if "301880" in rel else "OBC_SRC_V2", "")
    if real and os.path.exists(real):
        got = hashlib.sha512(open(real, "rb").read()).hexdigest()
        want = man.get((rel, "sha512"), "?")
        ok = got == want
        print(f"   {os.path.basename(rel)}: local copy {'matches' if ok else 'DOES NOT MATCH'} the manifest")
        if not ok:
            fails.append(f"{rel} checksum mismatch against the real source")
print("RESULT:", "PASS" if not fails else f"FAIL {fails}")
sys.exit(0 if not fails else 1)
