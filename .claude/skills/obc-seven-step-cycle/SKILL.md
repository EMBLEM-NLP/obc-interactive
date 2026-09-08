---
name: obc-seven-step-cycle
description: Execute one track of the OBC pipeline end to end under orchestration/PROTOCOL.md - DECLARE gates, BUILD in a copy, MUTATE (register H10 controls), INTEGRATE at real paths, RE-BAG, VERIFY from a clean tree with unmodified checks, AUDIT an addendum. Use when starting, resuming, or closing any track in orchestration/tracks.yaml.
allowed-tools: Read, Grep, Glob, Bash, Edit, Write, mcp__obc__*
---
# The seven-step cycle

Read the track's brief first: `orchestration/work-packages/<TRACK>.md` (or resource `obc://tracks`).

1. **DECLARE** — write `gates/GATES-<TRACK>.md` listing every gate before code. Format: `- [ ] ID: claim` / `CHECK:` / `EXPECT:`.
2. **BUILD** — in a copy of the tree (`isolation: worktree` if a subagent). Never edit `harden/checks/`, `ci/`, gate ledgers, or hooks — the `protect-checks` hook blocks it and the reason is in `references/rules.md` R1.
3. **MUTATE** — for every gate that reports a ratio, register a black-box control in `harden/checks/check35_controls.py` via the `write-h10-control` skill. Run `python3 harden/checks/check35_controls.py --db emitters/obc-mod.sqlite`. Every entry must read `ok`.
4. **INTEGRATE** — place files at real, convention-matched paths (stages in `retrieval/` or `pipeline/`, checks in the matching `checks/`, meta-checks in `harden/checks/`). Superseded files move to `superseded/` with a NOTE.md; they are never deleted.
5. **RE-BAG** — `bash ci/regenerate.sh && touch .regen.stamp`. Order is docs → self-manifest → provenance; out of order turns H3 and G16d red.
6. **VERIFY** — `python3 ci/run_gates.py`. Every gate the track touched must PASS. Corpus mode for completeness gates (`--all-articles`; the `guard-corpus` hook enforces it).
7. **AUDIT** — `append-audit-addendum` skill. Four sections, all mandatory.

**Stop and ask** — never assume — on any of the four decisions in `tracks.yaml` `decisions_pending`. The `decision-guard` hook blocks editing them out.

**Done means** step 7 is written and every declared gate passes in step 6 from a clean tree. Not step 2. Not step 4.

See `references/rules.md` for the ten rules and the defect each one is named for.
