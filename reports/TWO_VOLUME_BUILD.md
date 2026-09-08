# Both volumes built from one model. Volume 2 ledger: ALL MET.

```
vol2/GATES.md   ALL MET (7 met)
GATES.md        UNMET: 1 (met: 15)      # G16, the emitters
```

## Deliverables

| | pages | internal | **cross-volume** | web | dead | bookmarks | size |
|---|---|---|---|---|---|---|---|
| `301880_built_from_model_protected.pdf` | 1,260 | 35,862 | **993** | 445 | 0 | 4,138 | 19.5 MB |
| `301881_built_from_model_protected.pdf` | 1,001 | 0 | **4,382** | 71 | 0 | 927 | 27.6 MB |

Both AES-256, owner `ObcAdmin-2024`, opening freely with the ministry's original
permission set. Keep them in the same folder — the remote links reference each
other by filename.

**`See Note A-3.1.2.` in Volume 1 now opens Volume 2 at that note.** An Appendix A
note citing `9.10.16.1.` opens Volume 1 at the article. 5,375 links cross the
volume boundary in total, tinted green so they read as leaving the file.

Volume 2 having **zero internal links is correct, not a gap**: Appendix A is
explanatory material *for Division B*, so essentially everything it cites lives
in Volume 1.

## What the gates caught this round

**A regression, immediately.** My first cross-volume emitter was a rewrite rather
than an extension, and it silently dropped the categories it did not know about —
966 contents links, 149 amendment markers, 14 URIs. Check 8 failed with
`TOC: 578 missing`, `fewer URI links than v9`, `3 pages lost links`. I rebuilt it
as an extension of the existing emitter instead. Without the ledger this would
have shipped as "36,714 links, more than before".

**Two more checks were wrong, not two more defects.**

Check 8 verified a citation's target against a page index *in Volume 1* — for a
cross-volume target that is a different document. 292/300 until it routed
Volume 2 targets to Volume 2. **Seventh time.**

Check 15 scraped a number out of each link rectangle to identify what was cited.
That picks up neighbouring objective codes (`[F02-OS1.5]`), takes the first
number in a range (`1.1.2.1 to 1.1.2.3`), and cannot distinguish a documented
ancestor fallback from an error. 94% until it verified against the model's own
records — exactly the fix check 8 had already needed. **Eighth time.**

The pattern is now unambiguous. Every one of these was a check that only knew
about the shapes present when it was written: node types, page indexes within one
file, text scraped from a rectangle. The pipeline generalised; the tests kept
not.

## How unlazy carried this

1. **Gates existed before the work.** V7 was written when Volume 2 was uploaded,
   sat unmet through the container model and the merge, and closed only when a
   real check passed.
2. **`--status` before `--approve`.** Commands are printed and left unexecuted
   until explicitly approved; approval binds command, expectation, cwd, shell,
   timeout and `PATH`.
3. **Evidence is a fingerprint, not a claim.** Each PASS records a SHA-256 of the
   parsed definition and of the output, so an edited check invalidates its own
   evidence.
4. **Nothing was dropped quietly.** G16 is still `UNMET`, not abandoned, so
   "Volume 1 complete" stays false.

## Remaining

| | |
|---|---|
| **G16** | markdown / html / sqlite emitters — unmet, not abandoned |
| — | 32 Volume 1 notes with no Appendix A entry; 2 Form references unkeyed |
| — | Volume 2 has no page labels, and its tables are not reconstructed (stages 4–5 were not run on it) |
| — | 21 Volume 1 tables unbound; 182 standards absent from Table 1.3.1.2. |
