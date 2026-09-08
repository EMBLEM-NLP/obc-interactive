# Track audit — revision 5

After the Claude Code implementation pass. Revisions 1–4 preserved unedited.

**Headline: the enforcement layer exists and every piece of it was tested — as scripts, against Claude Code's exact stdin format, with fail-closed semantics proven on garbage input. Claude Code itself was not run here, and nothing is proven under the host until it is. The first version of every hook failed open; that defect is the finding of this pass.**

---

## What was built, and how each piece was verified

| artifact | verified how | verified under Claude Code? |
|---|---|---|
| `.claude/hooks/protect-checks.sh` | 6 cases: blocks edits to checks, ledgers, CI, hooks; allows stages and packages | **no** |
| `.claude/hooks/guard-commit-and-corpus.sh` | 7 cases: blocks commit without regen stamp or after a post-regen edit; blocks `check33b` without `--all-articles`; blocks reading source PDFs by path; allows the built PDFs | **no** |
| `.claude/hooks/decision-guard.sh` | 3 cases: blocks flipping FRULES off `conditional`, blocks deleting DEC1; allows marking A4 done | **no** |
| `.claude/hooks/gate-complete.sh` | 3 states: `stop_hook_active` → exit 0 immediately; broken registry → exit 2; green tree → exit 0 **only after `regenerate.sh`** | **no** |
| `.claude/hooks/_input.py` | garbage stdin → every hook exits 2 | **no** |
| `.claude/settings.json` | JSON valid; 19 denies; deny list and `protect-checks` agree on 10/10 probed paths after one gap fixed | **no** |
| `.claude/skills/*` (5) | frontmatter parses; `rebuild-validate-bag/scripts/rebag.sh` runs end-to-end and both validators PASS | **no** |
| `.claude/agents/{build,verify,embed}-track.md` | frontmatter parses; fields match the documented set | **no** |
| `.mcp.json` + `obc://` resources and prompts | 6 tools, 3 resources, 1 template, 2 prompts listed; `obc://capabilities` and `obc://provision/B/9/9.32.3.8` read; prompt rendered | tools: yes (MCP SDK); host: **no** |
| computed `cannot` list + `check38_capabilities.py` (G2c) | 5 of 6 probes fire on the real graph and clear when the capability is seeded; the sixth (semantic) clears when G1 lands | yes — it is a gate on the board |
| `CLAUDE.md`, `ci/fetch_sources.sh`, `.github/workflows/gates.yml` | YAML parses; fetch script verifies sha256 against the manifest before exporting | **no** — never executed |

The "verified under Claude Code" column is uniformly **no** for the host-invoked pieces, and this document will not say otherwise. The hooks are shell scripts that read JSON and exit 0 or 2; that behaviour is proven. That Claude Code calls them at the right moment with the right JSON is documented behaviour I have not observed. The first action in Claude Code is a trivial track with the hooks live, watching each fire.

---

## The finding: every hook failed open

The first version of all four hooks used `jq` to parse stdin, following the research report's sample code. `jq` is not installed here. The test harness reported **every block case as exit 0** — sixteen of sixteen wrong in the same direction.

The cause was not just the missing binary. The hooks were written `P=$(… | jq …); [ -z "$P" ] && exit 0` — *couldn't parse* was treated as *allow*. On any machine without `jq` — a fresh container, a developer laptop, a runner image without it — the entire enforcement floor would have silently vanished while every hook appeared installed and every session appeared governed.

Rewritten: a shared `_input.py` parses with Python (guaranteed present; the project is Python) and exports shell variables; every hook checks `HOOK_OK` first and **exits 2 with a reason if input cannot be parsed**. Garbage on stdin now blocks. Sixteen of sixteen cases correct.

This is the same defect class as everything else this project has found — a guard that reports "fine" for a reason unrelated to the thing it guards — arriving in the enforcement layer itself, in the first hour. Rule R1 applies to hooks: **a hook that cannot go red is a light, not a gate.** The test harness that caught it is now `ci/test_hooks.sh`, registered as gate **E1** on the board, so a future hook edit that fails open turns something red.

---

## Two more findings from building

**The completion gate caught me.** `gate-complete.sh` on a green tree returned exit 2. Not a bug: I had added the hook files without running `regenerate.sh`, so `MANIFEST.sha256` was stale and G16d was red. The hook blocked exactly the sequence the protocol forbids. It passed after regeneration. That is the first time the enforcement layer stopped a protocol violation — and the violator was its author.

**The `semantic` probe measured the wrong thing.** First draft: "does `vec_article` exist?" It does, so the probe did not fire — but `search()` doesn't query it, so the capability is absent. The probe now inspects whether the search code path references the index. It fires today and clears when G1 wires hybrid retrieval. A probe that checks the wrong precondition is a hand-written list with SQL decoration.

---

## The `cannot` list is now a gate

Before: seven sentences someone typed, one of which was already inaccurate. After: six probes, each with the SQL that establishes it, returned with the answer. `check38_capabilities.py` seeds each capability into a copy of the database and requires the line to disappear:

```
applicability  fires=yes  seeded->clears=yes
objectives     fires=yes  seeded->clears=yes
temporal       fires=yes  seeded->clears=yes
rules          fires=yes  seeded->clears=yes
heading_notes  fires=yes  seeded->clears=yes     (44 today; B3 drives it to 0)
semantic       (clears when G1 lands)
```

When F-scope adds occupancy nodes, the applicability line disappears without anyone editing anything. An agent reading `obc://capabilities` gets the graph's own statement of its limits, not a person's memory of them.

---

## Board

```
41 gates | failed 0 | known-review 1 (G7) | skipped 7
new: H10 (check35) in full mode; G2c (check38, computed cannot list); E1 (test_hooks.sh, 19 hook cases)
```

Bag rebuilt through the `rebuild-validate-bag` skill script; `check21` and `check26` PASS unmodified.

---

## Track status

| track | status | change |
|---|---|---|
| A1, A2, A3, PORT | DONE | — |
| **ENFORCE** (new) | **DONE — scripts verified, host unverified** | hooks, settings, skills, agents, MCP, CLAUDE.md, CI workflow |
| G | surface DONE; **G2 DONE**; G1, G3, G4 planned | computed `cannot` list with its own control |
| A4 | READY | critical path; work package and agent spec exist |
| C, E, MAINT | READY | — |
| B, FSCOPE, D, FOBJ | blocked | — |
| FRULES | conditional on DEC1 | `decision-guard` blocks any agent flipping it |

**Honest tally: 7 of ~31 done** (A1, A2, A3, PORT, ENFORCE, G surface, G2). Revision 4 said five.

---

## What migration to Claude Code now requires

1. Copy the integrated tree into a git repository. Everything under `.claude/`, `.mcp.json`, `CLAUDE.md`, `.github/` is already in place.
2. `pip install pymupdf pyyaml bagit sqlite-vec sentence-transformers`.
3. **Run one trivial track with hooks live and watch each fire.** Edit a check → `protect-checks` blocks. `git commit` without regen → `guard-commit` blocks. End the session → `gate-complete` runs check35 and the board. Until this is observed, ENFORCE is "scripts verified."
4. Push; watch `gates.yml` run once. Until it is green on a hosted runner, CI is "written."
5. Set `OBC_PDF_URL_V1/V2` and `ANTHROPIC_API_KEY` as repository secrets. The URLs live nowhere else.

Then A4, via `@build-track` with the A4 work package. It is the critical path and its spec is written.

---

## Not done, stated plainly

A4, B, C, E, MAINT, FSCOPE, D, FOBJ, FRULES: unchanged. G1, G3, G4: unchanged. The four decisions: still pending, now mechanically protected from being assumed away. The shipped `obc.sqlite` still carries the wall-clock date until Track B. The 313 figure assets are still unpackaged. Nothing in this pass moved any of them, and this document does not claim it did.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.

---

## Addendum, 2026-09-08 — self-audit acted on

Asked what I missed, I probed rather than recalled. Five findings, four fixed.

**1. The artifact I ship was not the artifact my script consumes.** `ci/fetch_data.sh` accepted only individually-flattened release assets (`emitters__obc-mod.sqlite`), a convention I invented, documented nowhere, and never executed — while the project ships `obc-interactive-data.tar.gz`. Rewritten to take a tarball (HTTP or local path), with staged installation: every file is hash-verified *before* anything is written. Tested against a live HTTP server, and against a deliberately corrupted archive, which aborts and leaves the tree untouched.

**2. A data-less clone crashed instead of reporting.** `run_gates.py` copied `emitters/obc.sqlite` into a working set before DATA1 ran, dying with a `FileNotFoundError` traceback. DATA1 exists to say what is wrong; it was never reached. It now gates the board and aborts cleanly.

**3. Worse — `ci/regenerate.sh` failed silently in the same state.** `make_provenance.py` needs the built PDFs, so it crashed and left `MANIFEST.sha256` *stale*, listing 29 files that do not exist. Every later gate would have verified against fiction. Caught because a diff read "0 lines differ," which was too clean to be true. Both now refuse with a stated reason.

**4. `ci/fetch_sources.sh` died off-runner** on `$GITHUB_ENV` under `set -u`. Guarded.

**5. The embed path had never been run, and running it produced the strongest result of the pass.** Installing the stack required CPU-only torch (the default CUDA wheel is ~2.5 GB and hit ENOSPC twice). Then:

- **R1, R3, R5 — skipped on every board in this project's history — executed and PASS**, including R5's scrambled-vector control.
- **`stage19_embed` reproduced `vectors_sha256` bit-for-bit** (`7ae68f5572ef…`) on a different machine, a different torch build, and CPU-only. That is a stronger determinism property than the board claimed, and it validates Track B's one-batched-re-embed plan.

**And a defect I introduced while recording it.** Making the embedding check unconditional in `check20` turned a ~30 s gate into ~5 min — inside the gate the `gate-complete` Stop hook runs on every session end. That is precisely the hook-timeout hazard flagged in the environments research, created by me, an hour after reading the warning. Now behind `OBC_CHECK_EMBED=1`. Separately, R1 at 216 s is marked `slow` so `--fast` (what the hook uses) omits it, while CI runs the full board with the deep check enabled.

**Still not done:** `verify-track` and `embed-track` specs unexercised; Claude Code never run; the workflow never executed; A4 onward untouched; the `obc.sqlite` wall-clock date still shipped; 313 figure assets still unpackaged; four decisions unanswered. Seven of ~31 tracks. Today moved no track — it made three failure modes visible that would otherwise have surfaced on someone else's first clone.
