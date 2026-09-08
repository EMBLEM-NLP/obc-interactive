# Migration to Claude Code — runbook

**Where this runs:** local CLI or the devcontainer for anything that executes gates; GitHub Actions for CI; the Claude Code GitHub Action only to summarise a board it did not produce. **Not** Claude Code on the web — its sandbox cannot fetch this repo's data and cannot run the 4-minute board comfortably. See `ENVIRONMENTS.md`.

**Readiness, stated precisely:** the tree is ready to *migrate*. It is not ready for *autonomous execution* until step 5 has been observed. Those are different claims and this document keeps them apart.

What "ready to migrate" was tested to mean, on 2026-09-07:
- `git init` + `git add -A` + commit on a copy stages 217 files, excludes every transient, keeps hooks executable
- from a clone **not** named `obc-interactive`, with `.git/` present: `ci/regenerate.sh` is idempotent (zero tracked changes) and two consecutive full board runs both PASS with zero tracked changes between them
- 19 hook cases pass as scripts against Claude Code's stdin format, including fail-closed on garbage input
- the MCP server finds its database from any working directory

What was **not** tested, because it cannot be here: anything Claude Code itself does. Hooks firing, skills loading, agents dispatching, `.mcp.json` connecting, the workflow running. Step 5 is where that happens, and nothing downstream of it should be believed before it.

---

## Steps

### 1. Create the repository — 15 minutes

Unzip `obc-interactive-repo.zip` (9 MB — code only; the 315 MB of derived binaries are deliberately not in it).

```
cd obc-interactive
git init -b main && git add -A && git commit -m "obc-interactive: control plane with enforcement layer"
```

**No Git LFS.** `.gitattributes` says why: Claude Code's cloud sandbox proxy rejects the LFS batch endpoint (anthropics/claude-code#25043, recurring as #60593), so LFS files clone as ~130-byte pointer stubs. A gate reading a stub instead of a 70 MB database reports zero rows, and a ratio over a zero denominator reports 100%. Instead the binaries live outside the repo, recorded in `data-manifest.json` with size and sha256.

Publish the data once — a GitHub release, S3, any object store — then:
```
OBC_DATA_URL=https://github.com/<owner>/obc-interactive/releases/download/data-v1 bash ci/fetch_data.sh
# or, from a local copy of the full tree:
OBC_DATA_DIR=/path/to/full/tree bash ci/fetch_data.sh
```
It verifies every file's sha256 before installing it and refuses on mismatch. Files already correct are skipped, so it is cheap to re-run.

**Proves:** the tree round-trips through git and the data arrives intact. `check40` (gate DATA1) runs first on every board and fails closed on a missing file, a wrong size, or an LFS pointer stub.

### 2. Environment — 5 minutes

Either use the devcontainer (`.devcontainer/`, reproducible, caches pip and the sentence-transformers weights across rebuilds) or install locally:
```
pip install -r requirements.txt
python3 ci/test_hooks.sh                              # 19 cases, RESULT: PASS
python3 ci/run_gates.py                               # full board incl. H10; ~4 min
python3 orchestration/schedule.py --check             # DAG consistent
```
Expect: 41 gates, 0 failed, 1 known-review (G7 — figure assets never packaged, Track E6), 4 skipped for the fetch-only source PDFs, and R1/R3/R5 PASS now that `sentence-transformers` is installed (they SKIP without it).

**Proves:** the board is green on this machine, not just the one that built it.

### 3. Secrets — 5 minutes, one human
In the repository settings, add: `ANTHROPIC_API_KEY`; `OBC_PDF_URL_V1` and `OBC_PDF_URL_V2` — download URLs for the two Crown-copyright source PDFs. `ci/fetch_sources.sh` verifies each download's sha256 against `ci/checks.yaml` before exporting it, and refuses on mismatch. The URLs live in secrets and nowhere else — not `.mcp.json`, not `CLAUDE.md`, not a hook, not a transcript. The `guard-source` hook blocks reading the PDFs by path in a session.

**Proves:** nothing yet. Enables G1, G8, V8, H9 in CI.

### 4. Push and watch the workflow — 10 minutes
```
git remote add origin <url> && git push -u origin main
```
`.github/workflows/gates.yml` runs on push: install → fetch sources → `regenerate.sh` → full board → CI1 (seeded failure must go red) → H10 → G2c → DAG check → upload `gate-board.json`. On a pull request it also runs `claude-code-action@v1` to post a one-comment summary, capped at 6 turns and $1.00, with `--permission-mode dontAsk` and only `Read` + `gh pr comment` allowed.

**Proves:** the workflow file, which has never executed, executes. Until this run is green, CI is "written," and `AUDIT-rev5.md` says so.

### 5. One trivial track with hooks live — 30 minutes, the step that matters
Open Claude Code in the repository and paste the prompt in `BOOTSTRAP.md`. Do not start A4. Do these four things and watch each hook fire:

| do | expect | hook |
|---|---|---|
| ask Claude to edit `harden/checks/check35_controls.py` | blocked, with the reason on screen | `protect-checks` + `settings.json` deny |
| ask Claude to `git commit` without running `ci/regenerate.sh` | blocked: "no .regen.stamp" | `guard-commit` |
| ask Claude to change FRULES to `ready` in `tracks.yaml` | blocked: "DEC1 must be answered by a human" | `decision-guard` |
| end the session | `gate-complete` runs check35 and the board before letting it end; ~4 min | `Stop` |

Then `@build-track` with the prompt "Track: ENFORCE-SMOKE — add one line to `orchestration/PROTOCOL.md` under Rules noting that hooks were observed firing on <date>, run the seven steps, and stop." Watch the `SubagentStop` hook run. Confirm `.claude/skills/*` were loaded (Claude will cite them) and `mcp__obc__capabilities` returns the computed `cannot` list.

**Proves:** the enforcement layer works under the host. This is the boundary between "migrated" and "ready for autonomous execution." Record the observation in `AUDIT-rev6.md`; until then, `tracks.yaml` `ENFORCE.evidence` correctly says *scripts verified, host unverified*.

### 6. A4, supervised — 3–5 days
```
@build-track Track: A4
```
The critical-path track. Its work package is `orchestration/work-packages/A4.md`; its agent spec is `.claude/agents/build-track.md`. Watch the first one. The Stop hook will refuse to let it finish until check35 and the board are green from the tree; the `verify-track` agent then re-runs everything from a clean checkout with no write tools. Only after A4 closes cleanly under hooks — twice would be better — is parallel worktree execution of C, E, and MAINT justified.

**Proves:** a track can be executed and verified by agents without a human re-running the chain. That was the reason for migrating.

### 7. Never, without a human
- Starting FRULES. `decision-guard` blocks flipping it; the human answer to DEC1 (assist or judge) goes in the commit message that changes it.
- Resolving DEC2, DEC3, DEC4 by editing them out.
- Committing the source PDFs. `.gitignore` excludes them; `fetch.txt` records what they must hash to.
- Editing verification machinery inside a track. Propose it in the audit addendum; a human merges it.

---

## What migration does not fix

The shipped `emitters/obc.sqlite` still carries the wall-clock date `2026-09-06` in `meta.generated` and will not byte-match a fresh rebuild until Track B regenerates it. The 313 figure assets are still unpackaged (G7 stays known-review). `search()` still does not query the vector index (G1). None of these move by migrating; they move by executing B and G under the hooks that migration turns on.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
