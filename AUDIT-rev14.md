# Track audit — revision 14

Orchestration: the schedule was wrong, and the DAG forbade its own work. Claude Code on the web, 2026-09-08. Revisions 1–13 preserved unedited.

**Headline: the project's "~17 weeks" was 7 weeks of parser bug on top of 10 weeks of guess, in a repository whose own rule R9 says numbers are measured and not typed — and it was the one number nobody had applied that rule to. Fixing it surfaced the larger thing: `tracks.yaml` instructed four `ready` tracks to produce files that `.claude/settings.json`, `protect-checks.sh` and `guard-machinery.sh` refuse to every executor, and PROTOCOL step 1 instructed **every** track to write its gate ledger there first. No track could take step 1. That had been noted in ENFORCE's evidence since revision 10 and stayed a note, because a sentence in an audit is not a mechanism.**

---

## WHAT MOVED

| item | evidence |
|---|---|
| The 17 weeks is gone | `schedule.py:weeks()` stripped every non-digit from the first token, so A4's `"3-5 days"` became the string `"35"` → 35 days → **7.00 weeks**. Now parses a range to its upper bound (`3-5 days` → 1.00 week) and **raises** on an unparseable string instead of defaulting to one week. Critical path 17 → **11 weeks**, typed. |
| The agent path is refused, not guessed | `agent_effort:` is `unmeasured` on all ten open tracks. `schedule.py` prints *"6 of 6 tracks on this path have never been dispatched"* rather than a smaller invented number. Replacing one fiction with a prettier fiction is not an improvement. |
| …and it cannot be quietly typed in | `schedule.py --check` fails any `agent_effort` that is neither `unmeasured` nor carries the word *measured*. Control: seeding `agent_effort: 2 days` into a copy turns `--check` red with the reason. |
| Gate E3 — the DAG must not specify what the guard refuses | `proposed/ENFORCE/check42_produces.py`. **16 findings before the rewrite, 0 after.** Reads `PROTECTED` from `check41_machinery.py` — a fourth consumer of one definition, not a fifth copy. `NEGATIVE=1` seeds a protected `produces` entry and requires detection: PASS. |
| The staging convention, R13 | `proposed/<TRACK>/<basename>` + a `promotes: [{from, to}]` map in `tracks.yaml`; PROTOCOL gains **step 4a PROMOTE**, a human act by construction. A4's `schema/proposed/` stopgap migrated into it — closes rev10 finding 3. |
| `orchestration/dispatch.py` — the wave planner | Imports `schedule.derive()` rather than reimplementing it. `--plan`, `--check`, `--promote <TRACK>`. **It plans; it never launches**, so it is exercisable on a clone with no data, no key and no dispatch — the state every audit here has been written from. |
| `integrate-track` — the role nobody owned | PROTOCOL steps 4–5 across worktrees. Mandatory `check41_machinery.py` **against the main checkout before every merge**, because git is fenced between worktrees and ordinary writes are not (R12). Roster 3 → 4. |
| MAINT declared no gates at all | Found by E3, not by reading. PROTOCOL step 1 had nothing to write for the track I had recommended dispatching first. M1 (a re-run over unmodified source diffs to empty) and M2 (a seeded amendment appears, and nothing else does) added. |

---

## WHAT DID NOT

Every track unchanged. **7 of ~31.** DEC1–DEC4 present and unanswered; FRULES conditional.

- **No track was dispatched.** Nothing here is measured; `agent_effort` still reads `unmeasured` everywhere, which is the honest state and the point of the field.
- **Nothing was promoted.** `check42_produces.py` and the E3 row for `ci/checks.yaml` sit in `proposed/ENFORCE/`. The gate that enforces the staging convention is itself staged — it is the first thing the promote step promotes, and until a human runs it E3 is not on the board.
- **The board still reports `E1 PASS, E2 PASS, DATA1 FAIL`.** The Stop hook blocked this session at `MISSING: 29`. Nothing in this pass makes a gate pass.
- The three unverified harness facts are still unverified: whether frontmatter hooks merge with or replace the `settings.json` hooks; whether `gate-complete` in a worktree gates the worktree or the main checkout; and R12's absence of filesystem isolation, which is accepted rather than fixed, with gate E2 named as the sole guarantee.

---

## WHAT BROKE

1. **My own approved plan specified a staging layout that does not work, and I proved it wrong forty minutes after writing it.** The plan said `proposed/` mirrors the real tree — `proposed/harden/checks/check36_schema.py`. `check41._candidates()` expands an absolute path into every suffix of itself, so that a worktree naming the main checkout absolutely is still caught (R12). It does not know what staging is:

   ```
   proposed/harden/checks/check36_schema.py                      -> ok
   /home/user/obc-interactive/proposed/harden/checks/check36…py  -> PROTECTED
   ```

   The same file, permitted spelled relatively and refused spelled absolutely. That is R12's defect running the other way, and a permission that depends on spelling is not a permission. The flat per-track layout has no suffix that can match a pattern needing `harden/checks/`, `gates/GATES-` or `ci/`. Recorded as **R14**, with `check42 --layout` printing the four-row table as standing evidence.

2. **My first `dispatch.py` dropped four tracks off the plan and said nothing.** FSCOPE, D, FOBJ and FRULES were neither dispatched nor held, because they depend on G, which is held on DEC1 and so never "completes" for the speculative waves to build on. They simply fell out of the loop. Caught by `--check`, which I had written to compare the plan against `schedule.py` — the first time in this project a checker of mine found my own defect before I did. The terminal wave now accounts for every remaining track with a derived reason.

3. **`guard-commit` deadlocks on a data-less clone, and this revision was committed by bypassing it.** It refuses any commit without `.regen.stamp`; the stamp is gitignored and transient; `ci/regenerate.sh` exits 1 without the 323 MB of derived data. So on a fresh container with no data there is no route to a commit, and `CLAUDE.md`'s own instruction — `bash ci/regenerate.sh && touch .regen.stamp` — cannot complete, because the `&&` never fires. The stamp was touched directly, with the user's explicit authorisation, and the reason it is defensible here is narrow and checkable: `git status` shows `README.md`, `FACTS.json` and `MANIFEST.sha256` unmodified, and nothing in this diff feeds them. **The regenerate is owed on the first run with data**, alongside the `FACTS.json` `abandoned` drift revision 12 left. It is very likely the same route the previous fifteen commits on this branch took; the difference is that this one says so. The durable fix — a no-data path in the hook, permitted only when no generated artifact is in the diff — is a protected edit and is staged, not applied.

4. **A verification I wanted to run was refused, correctly, by my own guard.** Copying `check42` to `harden/checks/` to test it from its promoted path was blocked by `guard-machinery` on screen. The rule holds against its author, which is the only interesting test of it; the root-walk was verified instead by calling `_root()` with the promoted, staged and deeper paths — all three resolve to the package root.

---

## WHAT WAS FOUND

### 1. The contradiction was four revisions old and had a note where a mechanism belonged

`tracks.yaml` told A4 to produce `harden/checks/check36_schema.py`, G to produce `check38_capabilities.py` and `check39_tools.py`, D `check36_modality.py`, FSCOPE `gates/GATES-scope.md`. Every one matches `PROTECTED`. PROTOCOL step 1 was worse, because it applied to all fifteen: *"DECLARE gates in `gates/GATES-<track>.md` BEFORE writing code."*

So the first action of every track was a refused write, and the four tracks the scheduler reported as `ready` were not. Revision 10 recorded it inside ENFORCE's evidence block — *"a track is specified to produce harden/checks/* and gates/GATES-*.md, which the guard refuses to every executor"* — and revisions 11, 12 and 13 each rewrote part of the protected set without touching it. R11 says a constraint is a mechanism or it is decoration; the same is true of a known defect. E3 is the mechanism, and it went red on 16 findings the moment it existed.

### 2. The schedule was the last unmeasured number in the repository

R9 was written for `README.md` and extended to `reports/*.md` by track E7. It was never pointed at `tracks.yaml`. The `effort:` field was typed by hand, summed by a function with a parsing bug, printed by `schedule.py`, and quoted onward into the audits and the handoff as though it measured something. H3's floor at three digits could not have caught it either — these are one- and two-digit figures, the same blind spot revision 12 found in the completion table.

The field is now `human_effort:` (typed, and labelled as typed) beside `agent_effort:` (`unmeasured`, and mechanically prevented from being anything else without a citation). Six of the ten open tracks would be affected by agent dispatch; **none has ever been dispatched**, so the honest number of agent-weeks for this project is not smaller than 17 — it does not exist.

### 3. What actually gates the schedule, once the parser is fixed

The planner puts three tracks in the dispatchable wave — A4, E, MAINT — and **holds C on DEC2**, which my plan had predicted would be in wave 1. After wave 2 (B alone), the plan runs out: G holds on DEC1, and FSCOPE, D and FOBJ are unreachable behind it. FRULES is conditional on DEC1 too.

So beyond about two waves, this project is not rate-limited by executors at all. It is rate-limited by four decisions and one data publication, and every one of those is a person. That is the answer to the question that prompted this revision, and it is worth more than the corrected week count.

---

## Tally and next action

**7 of ~31 done.** No track moved. The number of *dispatchable* tracks went from 0 to 3.

1. Publish the data tarball; set `OBC_DATA_URL`, `OBC_PDF_URL_V1`, `OBC_PDF_URL_V2`, `ANTHROPIC_API_KEY`. Unchanged from revisions 10–13, and now blocking three ready tracks rather than none.
2. Run `bash ci/regenerate.sh` the moment data exists — this commit owes one, and so does revision 12's `abandoned` drift.
3. Promote E3: `python3 orchestration/dispatch.py --promote ENFORCE`, review both diffs, install, confirm `check41_machinery.py` is green and E3 appears on the board.
4. Answer DEC1 and DEC2. DEC2 holds C out of wave 1 today; DEC1 ends the plan at wave 3.
5. Dispatch **one** track end to end — MAINT — and write its measured wall-clock into `agent_effort`. One measured track is the first honest input this schedule has ever had.
6. Settle the three harness facts at the first wave boundary.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.

---

## Addendum — CI run 15, observed after this revision was committed

Revision 13 stated that the `HAS_DATA` expression form could not be verified from here, and named its three possible outcomes. Run 15 (`9380139`, 2026-09-08T17:58Z) settles it on the intended one. Recorded here rather than by editing revision 13 (R10).

| step | result | what it establishes |
|---|---|---|
| hooks are falsifiable (E1) | success | unchanged |
| **DAG consistency** | **success** | ran above the fetch for the first time. It carries this revision's `agent_effort` validation, so R9-on-the-schedule is enforced on a hosted runner and not only locally. |
| **fetch derived data** | **skipped** | `HAS_DATA: false`. **`secrets` in job-level `env`, read from a step-level `if:`, is valid and evaluates.** Not a parse error, not a truthy string. |
| note that the fetch was skipped | success | the warning and the step summary fire, and the conclusion is unchanged — which was the point of making them advisory. |
| fetch Crown-copyright sources | success | `fetch_sources.sh:8` exits 0 with a stated reason when `OBC_PDF_URL_V1` is unset, and the source gates SKIP through `needs:`. A green step that fetched nothing and says so. |
| **regenerate** | **skipped** | revision 13's correction to the proposal. Without this guard the board stays skipped and DATA1 never runs, which was the entire point of the change. |
| gate board | **failure at DATA1** | `E1 PASS, E2 PASS, DATA1 FAIL`. One red, named, with its 29 files listed. |
| upload-artifact | **success** | `gate-board.json` exists, so `if-no-files-found: error` is no longer a second red step. |

**E2 passed on a fresh runner.** First hosted confirmation of `5dc7d41`'s `git update-index --refresh` fix, which was written for a false red that appeared only on a runner's cold index and was invisible in the interactive session that produced it.

Two of revision 13's three unverifiable items remain unverifiable: a run with the data secret actually set, and a fork pull request. The fork case is the no-false-green property — secrets are withheld, so the guard should skip the fetch and DATA1 should still fire red.

**Gate E3 is not on this board.** `check42_produces.py` is staged, not promoted, so CI does not run it. It appears only after `dispatch.py --promote ENFORCE`.

### Found while writing this addendum: running E1 disarms committing

`ci/test_hooks.sh:128` ends with `rm -f .regen.stamp`, and it must — line 39 tests that `guard-commit` blocks a commit when the stamp is absent, so the suite has to be able to remove it. The consequence is that **every local verification sweep leaves the tree in the state the commit guard refuses**, and the deadlock recorded in WHAT BROKE 3 re-arms itself after each one rather than being a one-time condition of a fresh container.

It also means the two guards interact in a way neither states: E1 proves the hooks can go red by removing the artefact the commit hook requires. Nothing is wrong with either in isolation. The durable fix belongs with the no-data path already proposed for `guard-commit` — have `test_hooks.sh` restore the stamp it found, or have the hook distinguish "no stamp" from "stamp older than a generated file". Both are protected edits, so both are proposals, not changes.

*(This addendum was committed by the same authorised `guard-commit` bypass recorded in WHAT BROKE 3. The regenerate remains owed.)*
