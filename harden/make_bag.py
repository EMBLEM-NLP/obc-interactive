#!/usr/bin/env python3
"""Build the deliverable as a BagIt bag (RFC 8493).

Payload = everything shippable. The two Crown-copyright source PDFs are recorded
in fetch.txt with their SHA-512 and length but not included, so a recipient who
obtains them legally gets byte-identity confirmed by the same manifest.
"""
import os, shutil, hashlib, sys
import bagit

SRC = "/home/claude/package/obc-interactive"
BAG = "/home/claude/package/bag"
SOURCES = [
    ("https://www.publications.gov.on.ca/store/20170501121/Free_Download_Files/301880.pdf",
     "/mnt/user-data/uploads/301880.pdf", "data/source/301880.pdf"),
    ("https://www.publications.gov.on.ca/store/20170501121/Free_Download_Files/301881.pdf",
     "/mnt/user-data/uploads/301881.pdf", "data/source/301881.pdf"),
]
if os.path.exists(BAG):
    shutil.rmtree(BAG)
shutil.copytree(SRC, BAG)
bag = bagit.make_bag(BAG, {
    "Source-Organization": "derived work; source published by King's Printer for Ontario",
    "External-Description": "2024 Building Code Compendium - unofficial interactive "
                            "edition and document model, current to 2025-01-16 "
                            "(through O. Reg. 5/25). Not the official version.",
    "External-Identifier": "Publications Ontario 301880 (Volume 1), 301881 (Volume 2)",
    "Bag-Software-Agent": "bagit.py + obc pipeline",
    "Internal-Sender-Description": "Payload files under data/source/ are the "
                                   "Crown-copyright source PDFs. They are NOT "
                                   "redistributed: fetch.txt records where to obtain "
                                   "them and the manifest records what they must hash to.",
}, checksums=["sha512", "sha256"])

# record the un-shippable inputs in fetch.txt and in the payload manifests
lines, man = [], {"sha512": [], "sha256": []}
for url, local, rel in SOURCES:
    n = os.path.getsize(local)
    lines.append(f"{url} {n} {rel}\n")
    for alg in ("sha512", "sha256"):
        h = hashlib.new(alg)
        with open(local, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 20), b""):
                h.update(chunk)
        man[alg].append(f"{h.hexdigest()}  {rel}\n")
open(os.path.join(BAG, "fetch.txt"), "w").writelines(lines)
for alg in ("sha512", "sha256"):
    p = os.path.join(BAG, f"manifest-{alg}.txt")
    with open(p, "a") as fh:
        fh.writelines(man[alg])
# tag manifests must be regenerated after editing the tag files
bag = bagit.Bag(BAG)
bag.save(manifests=False)
for alg in ("sha512", "sha256"):
    entries = []
    for name in sorted(os.listdir(BAG)):
        p = os.path.join(BAG, name)
        if not os.path.isfile(p) or name.startswith("tagmanifest-"):
            continue
        h = hashlib.new(alg)
        h.update(open(p, "rb").read())
        entries.append(f"{h.hexdigest()}  {name}\n")
    open(os.path.join(BAG, f"tagmanifest-{alg}.txt"), "w").writelines(entries)
print("bag built:", BAG)
b = bagit.Bag(BAG)
print("payload files:", len(list(b.payload_files())), "| algorithms:", sorted(b.algorithms))
