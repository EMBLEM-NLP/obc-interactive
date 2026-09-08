#!/usr/bin/env python3
"""Read link actions from the PDF structure, not from a viewer-level enum.

PyMuPDF's link `kind` is a convenience classification, and the control gate
proved it is not the same thing as the PDF action type:

  * the 819 "dead Launch links" in the source are actually /S /URI actions whose
    URI scheme is file:// - PyMuPDF reports those as kind 3 (LINK_LAUNCH)
  * a genuine /S /Launch action with an /F file spec is reported as kind 5
    (LINK_GOTOR), the same value as a legitimate cross-volume link

So "kind 3 == 0" does NOT establish "no dead file links". A real /Launch action,
or a /GoToR naming a file that does not exist, passes that assertion unseen.
These helpers assert on the action dictionary instead.
"""
import re

def actions(doc):
    """yield (page_number, xref, action_type, target) for every link annotation"""
    for i in range(doc.page_count):
        for xref, _atype, _id in doc[i].annot_xrefs():
            obj = doc.xref_object(xref, compressed=True)
            if "/Subtype/Link" not in obj.replace(" ", ""):
                continue
            s = doc.xref_get_key(xref, "A/S")[1]
            if not s:
                continue
            s = str(s).lstrip("/")
            if s == "URI":
                tgt = str(doc.xref_get_key(xref, "A/URI")[1] or "")
            elif s == "Launch":
                tgt = str(doc.xref_get_key(xref, "A/F")[1] or "")
            elif s == "GoToR":
                f = doc.xref_get_key(xref, "A/F/F")[1] or doc.xref_get_key(xref, "A/F")[1]
                tgt = str(f or "")
            else:
                tgt = ""
            yield i + 1, xref, s, tgt

FILE_URI = re.compile(r"^\s*\(?\s*(file://|//|\\\\\\\\|[A-Za-z]:[/\\\\])", re.I)

def dead_file_links(doc, allowed_remote=()):
    """Every way a link can point at a file instead of a place in the document."""
    out = []
    allow = {a.lower() for a in allowed_remote}
    for pg, xref, s, tgt in actions(doc):
        clean = tgt.strip("()").strip()
        if s == "Launch":
            out.append((pg, xref, "Launch action", clean))
        elif s == "URI" and FILE_URI.match(tgt):
            out.append((pg, xref, "file:// URI", clean[:60]))
        elif s == "GoToR":
            name = clean.split("/")[-1].lower()
            if name not in allow:
                out.append((pg, xref, "GoToR to an unexpected file", clean[:60]))
    return out
