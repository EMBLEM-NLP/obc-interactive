# Track audit — revision 16

The board, and what building it found in the id space. Claude Code on the web, 2026-09-08. Revisions 1–15 preserved unedited.

**Headline: asked for the track list somewhere durable, I built a generator rather than a page, because a hand-typed status page is this project's oldest defect in a new coat. Then four short questions about that page — what do the gates mean, what do the letters mean, what do the track letters mean — turned up that 10 gate ids name one thing in their ledger and another on the CI board, and that 10 more are simultaneously a track item and a gate. `E1` means three different things. Two of the collisions are mine, one of them made three days ago.**

---

## WHAT MOVED

| item | evidence |
|---|---|
| `orchestration/gen_board.py` | The board is generated from `tracks.yaml`, never typed. Imports `schedule.derive()` and `dispatch.plan()` rather than reimplementing them; the page prints only the *derived* status, never a track's typed `status:`. Reads `tracks.yaml` and git and nothing else, so it runs on a data-less clone — which `harden/gen_readme.py` cannot, and which is exactly where the state matters. |
| …and it is falsifiable | Determinism: two runs byte-identical. Falsification: seeding `MAINT: done` in a copy moves its card from `card ready` to `card done`, so the page demonstrably reads its input. Drift: `--check` PASS clean, FAIL after one appended comment, PASS after regenerating. |
| Gate glossary | **59** definitions: 56 from the ledgers, staged ones included, plus 3 stated as `exit_criteria` mappings in `tracks.yaml` (`CI1`, `CI2`, `S3`). Wrapped descriptions joined, `CHECK:`/`EXPECT:`/`EVIDENCE:` fields stopped at. Each gate chip on a card carries its assertion; the table gives id, text, where it is written down, mark, and which board script runs it. |
| Prefix and track indices | Both derived. A gate prefix names the ledger that owns it — and `H` and `R` are each used by two, so the prefix alone does not identify the owner. Track ids come in three layers: numbered `A1`–`A4`, single letters `B C D E G`, and names. There is no `F`: it split into `FSCOPE`, `FOBJ`, `FRULES`. |
| Gate **GID1/GID2** staged | `proposed/E/check47_gateids.py`. Compares each ledger entry's own `CHECK:` against what `ci/checks.yaml` runs (GID1) and finds ids that are both a track item and a gate (GID2). **FAIL 20.** Its `NEGATIVE` control exercises both halves separately, because the two assertions fail for different reasons. |
| **E10** filed under track E | Beside E7, which already owns document reconciliation. |
| Staged backlog | 10 → **15 ready of 25 declared**, across ENFORCE, A4, E and MAINT. |

---

## WHAT DID NOT

Every track unchanged. **7 of ~31.** DEC1–DEC4 unanswered. `agent_effort` `unmeasured` on all ten open tracks.

- **Nothing was promoted, and not for want of trying.** The user authorised it; `guard-machinery` refused the first `git mv` on screen. That is R13 working — a PreToolUse hook cannot know about an instruction, and the rule exists so an executor cannot install the checks that grade it. The commands were handed back.
- **The data release was not published**, because the data does not exist on this clone. `MISSING: 29` is not a stale pointer; there are no files to upload. DOC1-D2 and DATA1 both stay red.
- **Nothing was renumbered.** Both id collisions are filed, not fixed: renumbering either namespace would invalidate every `automatic-evidence` digest already recorded against the old id, which is a decision for a person and not a side effect of a board that wanted tidier labels.
- The board's hover definitions use `title=`, which is not keyboard-reachable and does not exist on touch. The glossary table is the accessible route; the tooltip is the enhancement.

---

## WHAT BROKE

1. **Both of my own drift checks would have been permanently red, and I caught it one commit after writing them.** `dispatch.py` and `gen_board.py` each recorded `HEAD` as the base their output was generated against. Committing the output moves `HEAD` past the SHA just written into it, so `--check` fails on the very next commit and stays failing. A false alarm on a schedule is the failure mode revision 13 named when `check41` fired on mtime — a gate that cries wolf gets ignored as thoroughly as one that never fires. Both now record the commit that last touched `tracks.yaml`, which is what they are actually functions of. Control confirms each still fires when that commit genuinely moves.

2. **I accused the repository of a defect that was my parser's.** Revision f59e29c reported `CI1`, `CI2` and `G2c` as "claimed by a completed track, defined nowhere" and called it a defect. They are defined: `CI1` and `CI2` as single-key mappings in A2's `exit_criteria`, `G2c` inside G's items and wired to `check38_capabilities.py`. `gate_defs()` read only `gates/GATES-*.md`, so anything written down elsewhere came back undefined. **This is the third verification in this project to fail for its own reasons rather than its subject's** — after revision 12's README row check that counted the digits in `volume1`, and revision 13's protected-set delta run from a scratch directory where `_PKG` resolved to a non-repo. The pattern is stable enough to name: *a checker that indicts the tree for its own blind spot is worse than no checker, because the instinct is to go and fix the thing it accused.* Corrected in `c45f598`; the finding survives in a narrower and truer form.

3. **The board over-reported twice, in opposite directions.** The headline read "24 staged to promote", counting declared `promotes:` entries from blocked tracks whose files do not exist — 14 were real. And the collision section reported 10 where 2 were genuine: two tracks naming one gate is ordinary when one introduces it and the other must not regress it. Both fixed. Burying two real findings under eight false ones is the same failure as missing them, and a count that overstates what a reader can act on is the defect class this project keeps finding, one level up.

4. **Checking a number in this very revision found a parser bug.** Rev16's draft said "56 definitions parsed"; the board reported 61. The five extra were `exit_criteria` mappings, and two of them were not gate ids at all — `E5 absence claims need H4 controls` and `S4 (H10)`, prose that YAML parsed as a mapping key because the sentence contained a colon. The glossary was listing sentences as gates. Filtered to keys shaped like an id; the true count is **59**. The habit that caught it is the only reason the number in this document is right, and it is the same habit that failed in WHAT BROKE 2 by being applied to the tree and not to the checker.

5. **A design pass caught two bugs a careful read had not**, which is the argument for taking the screenshot: `e()` escaped the ampersand in my own `&rarr;`, so only the first arrow in each agent chain rendered.

---

## WHAT WAS FOUND

### 1. Three ways past `guard-machinery`, none of them exotic

Found while preparing an authorised promotion: a dry-run copy into a scratch directory succeeded where its literal equivalent would have been refused. Probed the hook directly with crafted stdin, the way `ci/test_hooks.sh` does — **no writes performed, and no bypass used to promote anything**.

```
cp x harden/checks/evil.py                              refused
cp x /home/user/obc-interactive/harden/checks/evil.py   refused
D=/home/user/obc-interactive; cp x "$D/harden/..."      PERMITTED
cp x ${PWD}/harden/checks/evil.py                       PERMITTED
cd harden/checks && cp ../../x evil.py                  PERMITTED
```

`check41._candidates()` expands a path into every suffix of itself **only when `os.path.isabs()`**. The hook lexes the command before the shell expands it, so `$D/…` is not absolute at that moment and is tested as one literal string matching nothing. The third case needs no trick at all: the working directory moved, so the write target really is just `evil.py`.

This does not break the stated model — `check41`'s own docstring says prevention is a convenience and gate E2 is the guarantee, because no PreToolUse hook is sound against an executor holding Bash. What it means is that `guard-machinery` is **weaker than its twelve E1 cases suggest**: every existing case uses a literal path, so the suite measures the matcher on exactly the inputs the matcher handles. A guard whose tests are drawn from the guard's own assumption.

### 2. Ten gate ids name one thing in their ledger and another on the board

Every ledger entry carries its own `CHECK:` command; `ci/checks.yaml` independently maps an id to a script. Nothing compared them.

| id | the ledger says it asserts | ledger `CHECK` | the board runs |
|---|---|---|---|
| `E1` | SQLite answers the three queries the model was built for | `check16_sqlite.py` | `ci/test_hooks.sh` |
| `E2` | Markdown and HTML carry front matter and pass WCAG structure | `check17_emitters.py` | `check41_machinery.py` |
| `G7` | every citation resolves or carries a reason code | `check7_refs.py` | `check6_figures.py` |
| `G9` | the absence assertions in G8 can detect the defects they deny | `control_negative.py` | `check7_refs.py` |

…and `H6`, `H7`, `H9`, `V1`, `V4`, `V5` the same way. So the board prints a colour beside a gate whose ledger describes something the executed check never measured: **"G7 PASS" is `check6_figures` passing while the ledger says G7 means citations resolve.** `G7` and `G9` were hand-verified against the raw files before any of this was published — three earlier verifications here accused the tree for their own blind spot, and a fourth was not acceptable.

`GID1` reports and refuses to guess which file is right: resolving that needs the derived data and the ledgers' evidence digests, and a check that guessed would be inventing the answer it exists to detect.

### 3. Ten more ids are simultaneously a track item and a gate

Track items and gates are numbered independently and neither is namespaced.

- **`E1`** — item of E (*header-row flagging, 0 of 320 tables*) · gate in `GATES-emitters.md` (*SQLite answers the three queries*) · CI board (`ci/test_hooks.sh`). **Three meanings.**
- **`E4`** — item of E (*page 728 Volume 1, 7 orphaned body lines*) · gate in emitters (*manual accessibility review, **abandoned***).
- `E2`, `E3`, `E5`, `G1`–`G4`, `D1` the same way.

Tracks `D`, `E` and `G` are themselves gate-id prefixes, so `G1` reads either as the first gate of the Volume 1 ledger or the first item of track G, and nothing resolves which.

**I gave the user both `E4`s in a single listing earlier in this session without noticing they were different things** — which is the practical cost, and it happened to the person who had just read both files.

### 4. Two of the collisions are mine, and one is three days old

`E1` and `E2` already named emitter gates when the enforcement layer took those ids for `ci/test_hooks.sh` and `check41_machinery.py`. Then on 2026-09-08 I added **`E3`** — `check42_produces.py` — on top of an `E3` that was already in `GATES-emitters.md`, in the same pass that introduced a gate for detecting exactly this class of inconsistency elsewhere.

**Every "E1 PASS, E2 PASS" reported from this board — in revisions 14 and 15, in every CI summary quoted this session — is the enforcement pair and not the emitter pair.** The results are real. The labels are ambiguous, and were ambiguous before anything could show it.

---

## Tally and next action

**7 of ~31 done.** No track moved. The board went from not existing to generated, falsifiable and drift-checked; the id space went from unexamined to two gates and twenty findings, over 59 definitions and 43 board wirings.

1. **Promote the ENFORCE five first** — E3, DAG1, the `ci/checks.yaml` rows, the `guard-commit` worktree patch, the `guard-machinery` bypass fix. They gate everything else: E3 stops the DAG re-acquiring forbidden `produces`, DAG1 stops a stale merge silently reverting the schema, and the patch ends the deadlock where a live subagent blocks every commit on the main checkout.
2. **Publish the data release** and write the URL into `ci/fetch_data.sh`. Still the single action that closes the most — DOC1-D2 and DATA1 together, the `guard-commit` bypass, and `integrate-track`'s ability to merge rather than correctly refuse.
3. **Answer DEC1 and DEC2.** DEC2 holds track C out of the dispatchable wave today; DEC1 ends the wave plan at wave 3.
4. **Decide the id namespaces.** Renumbering invalidates recorded evidence digests, so the options are: namespace new ids by track, accept and document the overlap, or renumber and re-run the affected ledgers with data. GID1 and GID2 stay red until one is chosen — which is the honest state, not a regression.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
