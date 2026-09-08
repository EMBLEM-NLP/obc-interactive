---
name: append-audit-addendum
description: Write the audit addendum every track must return - what moved, what did not, what broke, what was found - with evidence digests and no retouching of earlier revisions. Use at step 7 (AUDIT) of every track.
allowed-tools: Read, Write, Bash
---
# The audit addendum

Append to `AUDIT-rev<N+1>.md`. Earlier revisions are never edited; corrections go beneath the finding they correct.

Four sections. All mandatory. Empty sections are stated as empty, not omitted.

## WHAT MOVED
Each item: track id, gate ids, the check that proves it, the number. `H1 PASS — check20_determinism, whole-file sha256 byte-identical across two fresh builds.` No number without the check that produced it (rule R9).

## WHAT DID NOT
Every track whose status is unchanged, listed. "Unchanged" is a claim and is stated.

## WHAT BROKE
Every bug in your own work, including patches that silently matched nothing (a regex assuming one space where the YAML had two; a one-element tuple without its comma; a guard that failed open when `jq` was missing). If you found none, say you looked and how.

## WHAT WAS FOUND
Every track so far has found something the previous one missed. State yours: the defect, the evidence, the track that now owns it.

End with the honest tally: `N of ~30 done` and the immediate next action, derived from `python3 orchestration/schedule.py`, not typed.
