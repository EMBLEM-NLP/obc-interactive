---
name: write-h10-control
description: Write a falsifiable H10 control for a ratio-reporting check - a registered mutation that must drive the gate below its floor. Use whenever adding, auditing, or being asked to trust any check that reports a percentage or ratio.
allowed-tools: Read, Grep, Bash
---
# Writing an H10 control

A ratio gate without a mutation that can break it is void, however green. Six such gates shipped in this project; every one had a real evidence digest.

## The contract
The control runs the **shipped check script** as a black box, twice:
- untouched working set → must exit **0**
- one input mutated → must exit **non-zero**

Both directions. A check that always fails passes a mutation-only test.

## Procedure
1. Find the ratio and its floor in the check (`grep -nE "fails.append|< 0\.|> 0\."`).
2. Find what the check **scores** (the mechanism: a pipeline output) and what it scores it **against** (the ground truth). Mutate only the former. See `references/mechanism-not-truth.md` — deleting the `ref` table shrinks both sides of a resolution ratio and leaves it at 100%.
3. Add a mutation function to `harden/checks/check35_controls.py` part 2 and a registry entry `(name, scope, script, mutation, args, env)`.
4. Run check35. If the entry reads **NEVER FAILS**, one of three things is true — determine which before touching anything:
   - your mutation did not reach what the check reads (check the path, the field, the type — `provenance` is a list, not a dict)
   - your mutation was too weak (try 100%; if 100% still passes, it is not weakness)
   - **the check cannot fail** — a corpus-wide aggregate with surplus, a gate on a label instead of a measurement, a digest that excludes the field that varies. Supersede it; do not tune it.
5. If it reads **NEVER PASSES** with exit 2, the script was not found — a cwd or path error, not a check failure.

You may not edit the check itself during a track. If the check is vacuous, write the replacement as `<name>b_*.py`, move the original to `superseded/` with a NOTE.md, and update the gate ledger — all as a proposal in the audit addendum for human review.
