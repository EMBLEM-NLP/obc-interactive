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

AUDIT-rev5.md; 16/16 hook cases correct incl. fail-closed on garbage input; gate-complete blocks a broken registry and passed a green tree only after regenerate; check38 PASS; MCP tools+resources+prompts listed and read; rebag skill script verified. Claude Code itself was NOT run - hooks are verified as scripts, not as invoked by the host. 2026-09-08: embedding stack installed (CPU-only torch); R1/R3/R5 executed for the first time and PASS; stage19_embed reproduced vectors_sha256 bit-for-bit on a different machine and torch build; fetch_data.sh rewritten to consume the shipped tarball and tested over HTTP incl. a corrupted-archive abort. 2026-09-08, Claude Code web, first observation under the host (AUDIT-rev6.md): guard-commit fired and blocked git commit without .regen.stamp; the Edit(harden/checks/**) deny blocked an edit to check35 before any hook ran; decision-guard did NOT block an Edit flipping FRULES to ready, nor an Edit deleting DEC1 - it parses new_string as a whole document, and a partial Edit never carries the tracks or decisions_pending keys it inspects. Under the host: 1 guard enforcing, 1 enforced by the deny list, 1 FAILED OPEN. Host status stays unverified for gate-complete (blocked once on the missing database, then allowed on retry). 2026-09-08, later the same day (AUDIT-rev7.md): the fail-open is closed. decision-guard now reconstructs the document an edit would produce (Write content, Edit old_string/new_string, MultiEdit edits) and judges that, refusing when no candidate can be built; both live Edit probes are blocked under the host. guard-commit now decides via _cmdstrip.py, which lexes the command and tests command position: the original regex ALSO failed open on bash -c wrapping and on git -C <path> subcommand form, beyond the heredoc false positive that exposed it. ci/test_hooks.sh 19 -> 35 cases; reverting decision-guard turns 5 red and reverting guard-commit turns 3 red, so E1 can no longer be green over either. gate-complete runs check40 first and names absent data instead of blaming H10. Still unverified under the host: protect-checks (the settings.json deny fires first) and the gate board itself (no data on this clone). 2026-09-08, third pass (AUDIT-rev8.md): the Bash write path into verification machinery is covered. Prevention is guard-machinery.sh, verified blocking under the host - touch harden/checks/probe.tmp was refused on screen and no file was created. The guarantee is gate E2, harden/checks/check41_machinery.py, which compares 90 protected files against HEAD with git diff-index (4 ms) and so sees the effect however produced; its NEGATIVE control seeds a mutation into a check in a copied tree and requires detection. PROTECTED in that check is now the single definition of verification machinery, replacing two lists that disagreed on four paths. ci/test_hooks.sh 35 -> 52 cases. Limit stated rather than glossed: a Bash guard cannot be sound against an executor holding Bash - a python heredoc calling open() modified a protected check with the hook live and was caught only by E2. 2026-09-08, fourth pass (AUDIT-rev9.md): checks carrying no_data run before the DATA1 abort, so E1 and E2 execute on a clone with no data. E2 has now run as part of the board (0.1 s, PASS) rather than standalone, closing the gap rev8 recorded. run_gates loop body extracted to execute(), shared by both paths and pinned by a synthetic-manifest control over PASS/FAIL/KNOWN/SKIP whose summary and per-gate statuses are identical before and after the change. Board on a data-less clone: ran 3, passed 2 (E1, E2), failed 1 (DATA1), where it previously reported DATA1 alone. 2026-09-08, fifth pass (AUDIT-rev10.md): first subagent dispatch in the project. Hooks fire for subagents inside worktrees; the settings.json deny list refuses a protected Edit before protect-checks sees it; decision-guard blocks an Edit flipping FRULES; SubagentStop fires. Both probes found fail-opens in guards written the same day. guard-machinery matched only repo-relative paths, so an absolute path reached the main checkout from a worktree - fixed, 4 cases. Bash scoping in the agent tools field is NOT enforced by the harness, so verify-track constrained nothing until the allowlist moved into guard-verify-readonly.sh - 12 cases. ci/test_hooks.sh 52 -> 68. Open and owned by this track: a track is specified to produce harden/checks/* and gates/GATES-*.md, which the guard refuses to every executor, so no track can complete as specified while enforcement is on; A4 stages to schema/proposed/ as a stopgap. Still unverified: whether frontmatter hooks merge with or replace the settings.json hooks, and whether a worktree subagent gate-complete gates the worktree or the main checkout.

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