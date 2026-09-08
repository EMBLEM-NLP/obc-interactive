# Work package — ENFORCE: Claude Code enforcement layer — hooks, settings, skills, agent specs, MCP

**Status in DAG:** `done`  ·  **Effort:** —
**Depends on:** A2  ·  **Unblocks:** (nothing downstream)

> First action in Claude Code: run one trivial track with the hooks live and confirm each fires. Nothing here is proven under the host until then.

## Produces

- `.claude/hooks/{protect-checks,guard-commit-and-corpus,gate-complete,decision-guard}.sh + _input.py (fail-closed)`
- `.claude/settings.json (19 denies, 4 hook groups)`
- `.claude/skills/* (5)`
- `.claude/agents/{build,verify,embed}-track.md`
- `.mcp.json + obc:// resources and prompts`
- `CLAUDE.md`
- `ci/fetch_sources.sh`
- `check38_capabilities.py`

## Gates to declare

- `CI1`
- `CI2`
- `G2c`

Every gate that reports a ratio needs a mutation in `check35_controls.py` that drives it below its floor. The mutation targets the mechanism, never the ground truth. Untouched must exit 0; mutated must exit non-zero.

## Evidence of completion

AUDIT-rev5.md; 16/16 hook cases correct incl. fail-closed on garbage input; gate-complete blocks a broken registry and passed a green tree only after regenerate; check38 PASS; MCP tools+resources+prompts listed and read; rebag skill script verified. Claude Code itself was NOT run - hooks are verified as scripts, not as invoked by the host. 2026-09-08: embedding stack installed (CPU-only torch); R1/R3/R5 executed for the first time and PASS; stage19_embed reproduced vectors_sha256 bit-for-bit on a different machine and torch build; fetch_data.sh rewritten to consume the shipped tarball and tested over HTTP incl. a corrupted-archive abort. 2026-09-08, Claude Code web, first observation under the host (AUDIT-rev6.md): guard-commit fired and blocked git commit without .regen.stamp; the Edit(harden/checks/**) deny blocked an edit to check35 before any hook ran; decision-guard did NOT block an Edit flipping FRULES to ready, nor an Edit deleting DEC1 - it parses new_string as a whole document, and a partial Edit never carries the tracks or decisions_pending keys it inspects. Under the host: 1 guard enforcing, 1 enforced by the deny list, 1 FAILED OPEN. Host status stays unverified for gate-complete (blocked once on the missing database, then allowed on retry).

## Completion checklist (PROTOCOL.md — none optional)

- [ ] 1 DECLARE   gates written to gates/GATES-ENFORCE.md before code
- [ ] 2 BUILD     in a copy of the tree, never in the bag
- [ ] 3 MUTATE    every ratio gate registered in harden/checks/check35_controls.py; check35 PASS
- [ ] 4 INTEGRATE real paths, orchestration wired, superseded files moved not deleted
- [ ] 5 RE-BAG    bash ci/regenerate.sh; rebuild; provenance regenerated
- [ ] 6 VERIFY    python3 ci/run_gates.py from a CLEAN bag — every touched gate PASS, corpus mode
- [ ] 7 AUDIT     addendum: what moved, what did not, what broke, what was FOUND
- [ ] tracks.yaml updated: own status, and any new item discovered filed under its track

Returning a pack of loose files is step 2. It is not done.

---
Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.