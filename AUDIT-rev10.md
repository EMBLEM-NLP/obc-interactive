# Track audit — revision 10

The first subagent dispatch, Claude Code on the web, 2026-09-08. Revisions 1–9 preserved unedited.

**Headline: subagents were dispatched for the first time in this project's history, and both of them found fail-opens in guards written earlier the same day. One was in code committed that morning; the other was in a fix committed an hour before the probe ran. The enforcement layer does reach inside a worktree — that part is now observed rather than assumed — but two of the three ways this project has tried to constrain an executor turned out to be decoration, and it took dispatching an executor to find out.**

---

## WHAT MOVED

| item | evidence |
|---|---|
| Subagents dispatched under the host, first time ever | `MIGRATION.md` step 5's outstanding item. Two agents, both `isolation: worktree`, both probing rather than working. `git worktree list` showed linked worktrees at `bef75a4` under `.claude/worktrees/`. |
| Hooks fire for a subagent inside a worktree | `guard-machinery` refused `sed -i` on `check35_controls.py` in both agents, verbatim, from inside the worktree. `decision-guard` refused an Edit flipping FRULES to `ready`, and `git diff --stat orchestration/tracks.yaml` came back empty. |
| The deny list fires before `protect-checks` | An Edit on a protected check returned *"File is in a directory that is denied by your permission settings."* `protect-checks` never ran. Revisions 6–9 recorded this as unobserved; it is observed now, and it is the deny list that acts. |
| `SubagentStop` fires | `gate-complete.sh` blocked both agents on exit with the missing-data message, then permitted them on retry. |
| Three agent specs corrected | `bef75a4`. All three now declare `isolation: worktree`, `Stop` **and** `SubagentStop`, and all four PreToolUse guards. `embed-track` had `MultiEdit` missing from `disallowedTools` and no isolation; `build-track` registered `gate-complete` on `Stop` only — not the event that actually fires for a subagent. |
| Two fail-opens closed | `803c456`. Detail below. |
| `guard-verify-readonly.sh` | A real allowlist for the verifier, default-refuse: 12 cases covering the board, `schedule.py`, `regenerate.sh`, reads and `sed -n` as allowed; redirection, `sed -i`, `python3 -c`, `bash -c`, `git checkout`, `rm` and unknown commands as refused. |
| `ci/test_hooks.sh` 52 → **68** cases | `RESULT: PASS`. E1 7.7 s on the board, E2 PASS. |
| `PROTOCOL.md` gains R11 and R12 | Each named for the defect that wrote it, in the style of R1–R10. |
| `.claude/worktrees/` gitignored | Without it, `git add -A` commits a full copy of the repository into the repository. |

---

## WHAT DID NOT

Every track unchanged. **7 of ~31.** `schedule.py --check` → `RESULT: PASS`; DEC1–DEC4 present; FRULES conditional.

- No gate that reads the graph ran. The board still reports `E1 PASS, E2 PASS, DATA1 FAIL`.
- **Whether frontmatter `hooks:` merge with or replace the `settings.json` hooks is still unverified.** Both agents declared hooks byte-identical to `settings.json`, so their firing is consistent with either. Distinguishing needs a marker hook present in one place only. The repo states it nowhere.
- A4 was dispatched as **step 2 only** and is in flight at the time of writing. It cannot close: step 6 is unreachable without data, and `PROTOCOL.md` forbids a `done` the source data does not reflect.
- CI still red at the data fetch. No `main`, no secrets, no PR. `MANIFEST.sha256` still stale.

---

## WHAT BROKE

1. **My own fix asserted a constraint that does not exist, within an hour of committing it.** I replaced verify-track's false sentence *"You have no write tools"* with a scoped `tools: Bash(python3 ci/run_gates.py*)` allowlist. The probe ran `echo hello > /tmp/verify_probe.txt` — nowhere on that list — with no prompt and no refusal. **Tools-field scoping is not enforced by the harness.** So the repair was the same defect as the thing it repaired, one layer up: a constraint written where nothing enforces it. It only became real once moved into a hook, which had been *observed* firing.
2. **`guard-machinery` failed open on absolute paths**, in code committed that morning. `touch /home/user/obc-interactive/harden/checks/check35_controls.py` **succeeded** and landed on the main checkout; the identical relative command was blocked. `_cmdstrip.py --writes` extracted the path correctly — the matcher in `check41_machinery.py` understood only repo-relative forms, returned nothing, and `[ -z "$HITS" ] && exit 0` waved it through. A subagent in an isolated worktree wrote to the main checkout this way.
3. **I designed a bypass that could not work and should not have existed.** Wanting a "loud" route for authorised machinery changes, I added `OBC_MACHINERY_CHANGE` to `guard-machinery`. A PreToolUse hook runs *before* the command, in its own environment: an `export` inside the command text can never reach it, so it was inert on its first use. A version that did work would be forgeable by any executor, and this guard's stated value is detection rather than prevention. Reverted. The sanctioned route was always a human reviewing the commit; I had mistaken the write for the checkpoint.
4. **`.claude/worktrees/` was untracked, not ignored.** One `git add -A` from committing a nested copy of the repo.

---

## WHAT WAS FOUND

### 1. Two of the three ways this project constrains an executor are decoration
Ranked by what the probes actually showed:

| mechanism | status |
|---|---|
| a sentence in an agent spec | **decoration** — verify-track said it had no write tools while holding `Bash` |
| `tools:` field scoping | **decoration** — not enforced; an unlisted redirection ran unrefused |
| `disallowedTools` | holds for `Edit`/`Write`/`MultiEdit`; untested against anything else |
| the `settings.json` deny list | **holds**, and fires before hooks |
| a PreToolUse hook | **holds**, including inside a worktree |
| gate E2 against HEAD | **holds**, and is the only one that sees effects rather than command text |

R11 is written for this. The general form: a limit is a mechanism or it is decoration, and only the mechanism is testable. Two of these were believed to be constraints by whoever wrote them, including me.

### 2. Worktree isolation fences git, not the filesystem
The harness refused a compound `git` command with *"names git in a form too complex to verify that it stays inside the worktree"* — so git operations are genuinely scoped. Ordinary filesystem writes are not: an absolute path reached the main checkout from inside a worktree. Isolation of an agent's *repository* is not isolation of its *machine*, and a path guard that only understands relative paths is therefore not a guard at all. R12 is written for this.

### 3. Tracks are specified to produce the very files executors may not write
A4's work package lists `harden/checks/check36_schema.py` among its products. `harden/checks/**` is protected: `guard-machinery` and the deny list both refuse it, correctly, because an executor that writes the check grading its own work has moved a gate rather than passed one. The same is true of `gates/GATES-<TRACK>.md`, which step 1 DECLARE requires every track to write.

So **no track can complete as specified while the enforcement layer is on.** This is not a bug in either half; it is a missing handoff. The resolution used for A4: author at `schema/proposed/`, and a human reviews and installs at the real path — which is exactly what `PROTOCOL.md` already says for machinery changes ("Propose the change in the audit addendum"), never generalised to the products a track is required to make. **Track ENFORCE owns closing this properly**, either by defining a staging convention in `PROTOCOL.md` or by narrowing the protected set to *existing* checks rather than the directory.

### 4. Correction to revision 6, and to `build-track.md`'s own text
Revision 6 wrote that the Stop hook "refuses to let a track finish until check35 and the board are green", and `build-track.md` still tells its agent *"The Stop hook runs check35 and the board and refuses to let you finish otherwise."* **Both are wrong.** `gate-complete.sh` line 6 honours `stop_hook_active`: it blocks once and permits on retry, as both agents demonstrated and as this session has demonstrated a dozen times. The gate is advisory. Nothing prevents a subagent finishing with a red board; what happens instead is that the failure is *visible*. That is worth having and it is not what was claimed. Rev 6 stays unedited; the correction lives here.

### 5. `CLAUDE_PROJECT_DIR` is unset in an agent's Bash but set for its hooks
Both agents reported it empty in the shell, while `bash "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-machinery.sh"` demonstrably resolved. So `guard-machinery`'s `ROOT="${CLAUDE_PROJECT_DIR:-.}"` is fine inside a hook but the fallback is doing nothing for us, and `gate-complete.sh` does `cd "$ROOT"` on the same value. Whether that root is the worktree or the main checkout is **unverified** — both trees were identical copies at the same commit, so nothing discriminated. If it is the main checkout, `gate-complete` gates a tree the agent did not edit.

---

## Tally and next action

**7 of ~31 done**, unchanged. What moved is that the enforcement layer was tested by the thing it exists to constrain, and lost twice.

1. Publish the data tarball; set `OBC_DATA_URL`, `OBC_PDF_URL_V1`, `OBC_PDF_URL_V2`, `ANTHROPIC_API_KEY`. Still item 1.
2. Create `main` from this branch and make it default.
3. Resolve finding 3 — the staging convention for track-produced checks and gate ledgers — before any track is expected to close.
4. Settle finding 5 with a marker hook: put one hook in `settings.json` that no agent frontmatter declares, dispatch, and see whether it fires.
5. Correct `build-track.md`'s claim about the Stop hook per finding 4.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
