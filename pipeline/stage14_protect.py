#!/usr/bin/env python3
"""Stage 14 - apply the ministry's permission set to the built PDFs.

Why this stage did not exist
---------------------------
It should have. README.md describes the shipped documents as "AES-256, owner
password `ObcAdmin-2024`, opening freely with the ministry's original permission
set (print yes, copy yes, change no)", and data-manifest.json declares
pdf/301880_built_from_model_protected.pdf and its Volume 2 twin as two of the 29
files the gates read. Nothing in this repository produced them. The only
encryption references in the tree were PDF_ENCRYPT_NONE, in the two injectors,
which deliberately write UNencrypted masters:

    pipeline/stage8b_inject.py:160        encryption=pymupdf.PDF_ENCRYPT_NONE
    pipeline/vol2/stage13_inject2.py:97   encryption=pymupdf.PDF_ENCRYPT_NONE

So the protected pair was made by hand, or by something never committed, and a
rebuild could regenerate every intermediate and still not produce two of the
declared artifacts. Found on 2026-09-09 by ci/rebuild_all.sh's preflight.

The determinism caveat, measured rather than assumed
----------------------------------------------------
**Encrypted output is NOT byte-reproducible, and cannot be made so.** PDF AES
encryption draws a random initialisation vector per run, so encrypting identical
content with an identical password twice yields different bytes. Measured here
on 2026-09-09 with pymupdf 1.28.2:

    unencrypted, saved twice : IDENTICAL
    encrypted   #1 sha256    : 0e6df785a9607924be5806272f748413…
    encrypted   #2 sha256    : 3f00d6beb3d69805c074f974b7539cb9…

This matters beyond this file. `data-manifest.json` carries a sha256 for both
protected PDFs, recorded from one encryption run in September 2026, and **no
rebuild will ever reproduce them**. That is a property of the format, not a
defect in the pipeline. H1/check20's determinism claim covers the masters, which
are genuinely reproducible; it cannot cover these two, and until now nothing said
so. What IS checkable about a protected file is asserted by --verify below:
that it opens without a password, carries the intended permissions, and holds
the same page content as its master.

    python3 stage14_protect.py                 # protect both volumes
    python3 stage14_protect.py --verify        # check existing protected files
    python3 stage14_protect.py --selftest      # prove the stage works, no corpus
"""
import argparse
import hashlib
import os
import sys

try:
    import pymupdf
except ImportError:  # pragma: no cover - the pipeline pins this in requirements.txt
    sys.exit("stage14: pymupdf is not installed (pip install -r requirements.txt)")

_PKG = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
OUT = os.environ.get("OBC_OUT", os.path.join(_PKG, "out"))
PDF_DIR = os.environ.get("OBC_PDF_DIR", os.path.join(_PKG, "pdf"))

# The ministry's original permission set, as README.md states it: print yes,
# copy yes, change no. ACCESSIBILITY is included deliberately - a legal code that
# a screen reader cannot extract text from is not accessible, and AODA
# (O. Reg. 191/11 s.14) is the reason the HTML emitter targets WCAG 2.2 AA.
PERMS = int(pymupdf.PDF_PERM_PRINT | pymupdf.PDF_PERM_COPY | pymupdf.PDF_PERM_ACCESSIBILITY)

# Published in README.md. It is an OWNER password: the document opens with no
# password at all, and this only gates changing the permissions. It is not a
# secret and never was - putting it in a repository secret would imply the
# documents are confidential, which they are not; they are Crown-copyright
# material licensed for free public redistribution.
OWNER_PW = os.environ.get("OBC_OWNER_PW", "ObcAdmin-2024")

VOLUMES = {
    1: ("301880_built_from_model.pdf", "301880_built_from_model_protected.pdf"),
    2: ("301881_built_from_model.pdf", "301881_built_from_model_protected.pdf"),
}


def protect(src, dst):
    """Write dst as src with the permission set applied. Returns dst's sha256,
    which will differ on every run - see the module docstring."""
    doc = pymupdf.open(src)
    try:
        doc.save(dst, encryption=pymupdf.PDF_ENCRYPT_AES_256,
                 owner_pw=OWNER_PW, user_pw="", permissions=PERMS,
                 no_new_id=True)
    finally:
        doc.close()
    return hashlib.sha256(open(dst, "rb").read()).hexdigest()


def verify(master, protected):
    """What is checkable about an encrypted file, given the bytes are not.

    Returns a list of failures; empty means good.
    """
    bad = []
    if not os.path.exists(protected):
        return [f"{os.path.basename(protected)}: absent"]
    doc = pymupdf.open(protected)
    try:
        # needs_pass is the property that matters to a reader: the document must
        # open freely. An owner password that also locked opening would be a
        # different document from the one README describes.
        if doc.needs_pass:
            bad.append(f"{os.path.basename(protected)}: asks for a password to open")
        # NOT doc.is_encrypted: that means "still locked", and it flips to False
        # the moment the empty user password auto-authenticates - so it reads
        # False for both an encrypted and an unencrypted file, and an assertion
        # on it is vacuous. The selftest's control caught exactly that. The
        # metadata field names the scheme: 'Standard V5 R6 256-bit AES' or None.
        scheme = doc.metadata.get("encryption")
        if not scheme:
            bad.append(f"{os.path.basename(protected)}: not encrypted at all")
        elif "AES" not in scheme:
            bad.append(f"{os.path.basename(protected)}: encrypted as {scheme!r}, expected AES")
        got = doc.permissions
        for name, bit in (("print", pymupdf.PDF_PERM_PRINT),
                          ("copy", pymupdf.PDF_PERM_COPY),
                          ("accessibility", pymupdf.PDF_PERM_ACCESSIBILITY)):
            if not got & bit:
                bad.append(f"{os.path.basename(protected)}: {name} not permitted")
        if got & pymupdf.PDF_PERM_MODIFY:
            bad.append(f"{os.path.basename(protected)}: change IS permitted, and must not be")
        if os.path.exists(master):
            m = pymupdf.open(master)
            try:
                if m.page_count != doc.page_count:
                    bad.append(f"{os.path.basename(protected)}: {doc.page_count} pages, "
                               f"master has {m.page_count}")
                elif m.page_count:
                    # Content equality on a sample: encryption must not alter text.
                    for i in (0, m.page_count // 2, m.page_count - 1):
                        if m[i].get_text() != doc[i].get_text():
                            bad.append(f"{os.path.basename(protected)}: page {i+1} text "
                                       f"differs from the master")
                            break
            finally:
                m.close()
    finally:
        doc.close()
    return bad


def selftest():
    """Prove the stage does what it claims, without the corpus.

    The Crown-copyright sources are fetch-only and the built PDFs are 19 and 27
    MB of derived data this clone does not have, so the stage is exercised on a
    document it makes itself. What is being tested is this file's behaviour, not
    the Compendium's content.
    """
    import tempfile
    d = tempfile.mkdtemp()
    master = os.path.join(d, "master.pdf")
    doc = pymupdf.open()
    for n in range(3):
        doc.new_page().insert_text((72, 100), f"page {n + 1}")
    doc.save(master, no_new_id=True)
    doc.close()

    a = protect(master, os.path.join(d, "a.pdf"))
    b = protect(master, os.path.join(d, "b.pdf"))
    fails = verify(master, os.path.join(d, "a.pdf"))

    print("  opens without a password, permissions correct, text matches the master:",
          "yes" if not fails else f"NO - {fails}")
    print(f"  two runs over identical input: {'identical' if a == b else 'DIFFERENT'}"
          f"  ({a[:12]} / {b[:12]})")
    print("  that difference is expected and is the point of the docstring:")
    print("  encrypted PDFs are not byte-reproducible, so data-manifest.json's")
    print("  sha256 for the two protected files can never be matched by a rebuild.")

    # The control. If verify() cannot fail, it is not verifying anything: hand it
    # the unencrypted master and require a complaint.
    ctrl = verify(master, master)
    print(f"  control, verify() over an UNencrypted file: "
          f"{'correctly rejected' if ctrl else 'ACCEPTED IT - verify() is vacuous'}")

    ok = not fails and a != b and bool(ctrl)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true", help="check existing protected files")
    ap.add_argument("--selftest", action="store_true", help="exercise the stage on a synthetic PDF")
    a = ap.parse_args()

    if a.selftest:
        sys.exit(selftest())

    fails, n = [], 0
    for vol, (master_name, prot_name) in VOLUMES.items():
        master = os.path.join(PDF_DIR, master_name)
        prot = os.path.join(PDF_DIR, prot_name)
        if a.verify:
            fails += verify(master, prot)
            n += 1
            continue
        if not os.path.exists(master):
            fails.append(f"{master_name}: absent - run the injector stages first")
            continue
        digest = protect(master, prot)
        print(f"  volume {vol}: {prot_name} written, sha256 {digest[:12]}… "
              f"(differs every run by design)")
        fails += verify(master, prot)
        n += 1

    for f in fails:
        print(f"  {f}")
    print(f"\n{n} volume(s) examined; {len(fails)} problem(s)")
    print("RESULT:", "PASS" if not fails else f"FAIL {len(fails)}")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
