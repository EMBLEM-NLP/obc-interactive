# check33_completeness.py — superseded, not deleted

Removed from the active check set 2026-09-07. Its metric is arithmetically
incapable of failing: `bundle()` unions in the exact `refs | terms` set that
`dependencies()` returns as `dep`, so `dep & bundle(nid) == dep` identically
for every node. Measured directly over the corpus: 11680/11680 = 100.0000%,
zero articles below the 0.99 floor. Gate R4 as originally written could not
have failed regardless of the underlying data.

Replaced by check33b_completeness.py, which calls the real assembler
(retrieval/lib/obc_context.py) and reports three separate claims — C1
reachability, C2 delivery, C3 usability — each with a registered mutation in
harden/checks/check35_controls.py that must drive it below its floor.

Kept here, unexecuted, as the historical record of the defect and the fix.
See gates/GATES-remediation.md.
