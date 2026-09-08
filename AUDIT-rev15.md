# Track audit — revision 15

Track **E, item E9 only**: the README described a tree the reader does not have.
Claude Code subagent in an isolated worktree, 2026-09-08. Revisions 1–14
preserved unedited.

*Numbered 15, not 14, by the orchestrator. The subagent wrote this as revision
14 and was right to: the worktree it was dispatched into was based on `5dc7d41`,
where the highest audit is revision 13. `AUDIT-rev14.md` already existed on the
branch, committed, with different content — so a stale base forked the audit
trail into two documents claiming the same revision. Only the number and this
note are changed; the subagent's text is otherwise as written, per R10.*

**Headline: the repository advertised 29 interactive artifacts it does not
contain and never said where to get them. The absence was declared three times
over — `.gitignore`, `data-manifest.json`, gate DATA1 — and the remedy was
declared nowhere: `README.md` contained zero occurrences of `fetch_data`,
`download`, `release`, `tarball` or `gitignore`. The front page is now split by
the tree it describes, and the half that cannot be honest yet — there is no
published release — is a gate that is red on purpose and was shown capable of
green. Track E stays `ready`; E1–E8 are untouched.**

---

## WHAT MOVED

| item | evidence |
|---|---|
| **E9 — `README.md` is the source-checkout page** | 165 lines. Names `ci/fetch_data.sh` **6 times** and all three source modes (`check44_distribution.py --only d1`, exit 0). States what a clone contains, what it excludes (**29 files, 338,348,579 bytes**, both read from `data-manifest.json` by the writer, not typed), and the three reasons — Crown copyright, size, and the Git-LFS-pointer hazard quoted from `check40_dataintegrity.py`'s docstring. |
| **E9 — `PACKAGE.md` is the package-at-package-time page** | 205 lines. Carries the `pdf/` table, the `emitters/` counts and example SQL, `model/`, `pipeline/`, `verify/`, the amendment reconciliation, the completion table and *What is still open*. Eight moved blocks confirmed present **verbatim** in `PACKAGE.md` and **absent** from `README.md`; the `## Licence and attribution` block is **byte-identical** in both to the original README. Re-derivable from `git diff -- README.md` plus `PACKAGE.md`; see WHAT BROKE 3 on the status of the script that measured it. |
| **DOC1-D1 PASS** | `python3 proposed/E/check44_distribution.py --only d1` → exit 0, `D1 PASS`. `29 of 29 (338,348,579 B of 338,348,579 B)` absent; README names the fetcher. |
| **DOC1-D2 FAIL, by design** | `python3 proposed/E/check44_distribution.py --only d2` → exit 1, `D2 FAIL`. **0 of 4** locations in `ci/fetch_data.sh` resolve: three are `https://…/` (ellipsis where the host belongs) and one is `https://<host>/<owner>/…`. No public release of the data exists. This is not softened, not a warning, and not deferred. |
| **The two halves fail independently** | `python3 proposed/E/check44_distribution.py` → exit 1, `DOC1 halves: D1 PASS, D2 FAIL`. Selectable with `--only d1` / `--only d2`; D1's green does not mask D2's red. |
| **DOC1-C1 — D1 can go red** | `--controls` → `C1 strip-pointer untouched exit 0 mutated exit 1 ok`. Mutation: 6 occurrences of `ci/fetch_data.sh` removed from a **temp copy** of the README. Reproduced by hand: `OBC_README=<stripped copy> … --only d1` → exit 1. The real `README.md` was never edited to run a control. |
| **DOC1-C2 — D2 can go green** | `--controls` → `C2 restore-placeholder repaired exit 0 placeholder exit 1 ok`. Reproduced by hand: a temp copy of `ci/fetch_data.sh` with one real URL substituted → `--only d2` exit 0, `1 of 4 resolve`. **This is the load-bearing half.** D2's shipped state is red; without a copy that passes, `D2 FAIL` would be indistinguishable from `sys.exit(1)`. The real `ci/fetch_data.sh` still holds 3 ellipses (`grep -o '…' \| wc -l` → 3). |
| **`ci/fetch_data.sh --where`** | exit 0. Prints the 29 absent files with sizes, then each of `OBC_DATA_TARBALL` / `OBC_DATA_DIR` / `OBC_DATA_URL` with what it must point at and an example, then `WHERE TO GET THE TARBALL: nowhere public, yet.` and why DOC1-D2 is red. 54 lines added; `bash -n` clean. The failure now names its own remedy. |
| **`harden/gen_readme.py` retargeted to `PACKAGE.md`** | `git diff -U1` shows **two executable lines changed**, both the output path (`open(f"{PKG}/README.md")` → `PACKAGE.md`, read and write). Everything else in the diff is docstring and comment. **Unexercised** — see WHAT DID NOT. |
| **E1 PASS** | `bash ci/test_hooks.sh` → exit 0, `RESULT: PASS`, **77 ok cases**, 0 failures. |
| **E2 PASS** | `python3 harden/checks/check41_machinery.py` → exit 0. `protected files tracked : 95`, `modified vs HEAD : 0`, `untracked additions : 0`. This is the proof that the split touched nothing protected, however it was produced. |
| **Board reaches its declared limit** | `python3 ci/run_gates.py` → exit 1: `E1 PASS`, `E2 PASS`, `DATA1 FAIL … MISSING: 29`, then `Not running the remaining gates - they would read wrong data.` Same three-line board as revisions 9–13. |

Files changed: `README.md`, `ci/fetch_data.sh`, `harden/gen_readme.py` (modified);
`PACKAGE.md`, `proposed/E/{GATES-E.md, check44_distribution.py, check22_docs.py}`
(new). Nothing committed. `orchestration/tracks.yaml` not touched.

---

## WHAT DID NOT

**Every track's status is unchanged.** Stated as a claim, from
`python3 orchestration/schedule.py`, not typed: done — A1, A3, PORT, A2,
ENFORCE (5); ready — A4, C, **E**, MAINT (4); blocked — B, G, FSCOPE, D, FOBJ
(5); conditional — FRULES (1). DEC1–DEC4 all present and unresolved.

- **Track E stays `ready`.** E9 is one item of nine. **E1–E8 were not touched**
  — every one of them needs the derived data and this clone has none. `done` is
  certified by `verify-track` from a clean bag, not by the executor.
- **`orchestration/tracks.yaml` was not edited at all**, on instruction. My copy
  is the pre-orchestration schema (`effort:`, no `promotes:`, no `agent_effort:`);
  merging it would have reverted the orchestrator's uncommitted work on every
  track. What I would have added is reported as text at the end of this section.
  I wrote no `agent_effort:` anywhere.
- **Step 5 RE-BAG is unreachable.** `bash ci/regenerate.sh` → exit 1:
  *"regenerate: data files are missing or are pointer stubs … Refusing to
  regenerate - a manifest built now would describe a tree that does not exist."*
  `MANIFEST.sha256`, the RO-Crate and the in-toto attestation are therefore
  **stale** with respect to `README.md`, `PACKAGE.md`, `ci/fetch_data.sh` and
  `harden/gen_readme.py`. **`.regen.stamp` was not touched** — creating it would
  assert a regeneration that did not happen, and `guard-commit-and-corpus`
  reads it.
- **Step 6 VERIFY is unreachable.** The board aborts at DATA1. DOC1 is not on
  the board at all and cannot be: `ci/checks.yaml` is protected. Its entry is
  proposed below.
- **H10 / `check35_controls.py` did not run.** `python3
  harden/checks/check35_controls.py --db emitters/obc-mod.sqlite` →
  `FileNotFoundError: emitters/obc-mod.sqlite does not exist`. No H10 entry is
  owed: **DOC1 reports no ratio and has no floor**, so R1 does not bite. Its two
  controls are carried by the shipped check itself, run as a black box in a
  subprocess, in both directions. Extending check35 with a package-level scope
  so they join H10 is proposed below, not applied.
- **`harden/gen_readme.py` is unexercised.** It opens `emitters/obc.sqlite` and
  both built PDFs. Nothing in this session establishes that the retargeted
  script runs. I did not stub the database to make it appear to: a green from a
  fabricated input is the failure mode this project has found six times.
- **The `gen_readme.py` "own the whole file" refactor was NOT done.** It is the
  right durable fix — the span-only rewrite is the mechanism behind
  AUDIT-rev12 finding 1 and behind E9 itself — and it is deliberately out of
  this pass, for the reason revision 9 named: the script cannot be exercised
  here. Proposed below.
- **`check22_docs.py`'s three-digit figure floor was NOT lowered.** Same
  reasoning; it is a separate change with its own blast radius, and shipping two
  untested changes to the documentation gate at once is how the thing being
  fixed got there.
- **`verify/emitters/checks/check19_package.py` was not updated**, though
  `PACKAGE.md` arguably belongs in its `REQUIRED` member list. It is protected.
  Proposed below.
- **`.gitignore` and `.gitattributes` were not corrected** for the size figure
  they get wrong (WHAT WAS FOUND 5). Neither is in E9's scope and the correct
  fix is to stop typing the number at all.
- **Not runnable in this worktree, therefore neither passed nor failed:**
  `orchestration/dispatch.py --check` and `proposed/ENFORCE/check42_produces.py`
  (gate E3). Both post-date `5dc7d41`; see WHAT WAS FOUND 1.
- **This session ended with a red board, and the Stop hook said so.**
  `gate-complete.sh` blocked once on
  *"BLOCKED: the data the gates read is missing, truncated, or a pointer stub -
  this is NOT a gate failure … MISSING: 29"*, then permitted the retry, as it is
  designed to. Recorded because finishing is not evidence that the board was
  green. It was not, for two declared reasons: **DATA1**, which no executor can
  clear on a clone with no data, and **DOC1-D2**, which is red on purpose and
  whose remedy — publishing the data release — is the same act. Nothing was
  worked around to satisfy the hook: no `.regen.stamp` was created, no data was
  stubbed, and no check was edited.

### Reported, not applied: track E's `promotes:`

To be added to `E:` in the orchestrator's copy of `orchestration/tracks.yaml`.
Every `to` is a protected path, which is why the file is staged rather than
written:

```yaml
  promotes:
    - {from: proposed/E/GATES-E.md,               to: gates/GATES-E.md}
    - {from: proposed/E/check44_distribution.py,  to: harden/checks/check44_distribution.py}
    - {from: proposed/E/check22_docs.py,          to: harden/checks/check22_docs.py}
```

Track E's `gates:` list should gain `DOC1` alongside `T1`–`T5`, and its `items:`
should gain:

```yaml
    E9: "README describes a tree the reader does not have; split README/PACKAGE, gate DOC1"
```

`E.status` stays `ready`. I wrote no `agent_effort:`.

### Also proposed, not applied

1. **`ci/checks.yaml`** — add DOC1 to the board once check44 is promoted. It
   needs no data, so it belongs with E1/E2 above the DATA1 abort:
   `- {script: harden/checks/check44_distribution.py, scope: ., gate: DOC1, no_data: true, note: D2 is red until the data release is published}`.
   The board will then be red for a second declared reason. That is the point.
2. **`harden/checks/check35_controls.py`** — a `pkg` scope in
   `SUBPROCESS_CONTROLS` that materialises the package root rather than a graph
   or a `verify/` working set, so DOC1-C1/C2 can be registered as H10 entries
   instead of living inside their own check. Its two existing scopes cannot
   express a document check.
3. **`harden/gen_readme.py`** — own the whole of `PACKAGE.md`, not the span
   between two headings, and generate the completion table from `led`. This is
   the durable fix for AUDIT-rev12 finding 1 and for E9's root cause. Needs the
   data to test.
4. **`harden/checks/check22_docs.py`** — lower the figure floor below three
   digits, so ledger counts like `16 of 16` come inside the gate.
5. **`verify/emitters/checks/check19_package.py`** — add
   `obc-interactive/PACKAGE.md` to `REQUIRED`, and decide deliberately whether
   its README phrase list should follow the split.

---

## WHAT BROKE

Four defects in my own work. Three were caught by running something; one by
reading.

1. **My split verifier failed, and it was right.** The script asserting that the
   completion-status block moved to `PACKAGE.md` *verbatim* reported
   `completion tbl … False`. Cause: I had inserted a one-paragraph E9 note
   *inside* the block I was asserting was unchanged. The verification was
   correct and my claim was wrong. Fixed by splitting the assertion into two
   anchored blocks either side of the insertion, and by marking the inserted
   paragraph in `PACKAGE.md` as added by E9 — **not** by deleting the assertion,
   which was the tempting move. Revisions 12 and 13 each recorded a verifier
   that failed for its own reasons; this is the opposite case, and it is worth
   recording that the instinct in both situations is identical.

2. **`--statements` was case-sensitive where H3 is not.** I wrote the
   required-statement helper with a plain `in` test for all six phrases. H3
   (`check22_docs.py`) matches through `lib/canon.contains(..., casefold=True)`;
   `check19_package.py` (G16d) does a plain `in`. The README says
   *"Current to 16 January 2025"* with a capital C, so the helper as first
   written would have reported `current to MISSING` against a README that
   satisfies H3 — a false red in the control I built to protect the split.
   Measured after the fact: `'current to' in flat` → `False`,
   `'current to' in flat.casefold()` → `True`. Fixed by carrying a per-phrase
   case-fold flag matching the owning check, with the strict form winning where
   both gates own a phrase. Found by reading `check22` and `check19` side by
   side before running, not by running.

3. **My two strongest pieces of evidence were produced by scripts that are not
   in the tree.** The verbatim-move proof and the offline exercise of the staged
   `check22_docs.py` figure test ran from the session scratchpad and are gone
   when the session is. Under R9 a number cites the check that produced it, and
   "a script I wrote and did not keep" is a weak citation. Both claims are
   re-derivable from the repository — the moves from `git diff -- README.md`
   against `PACKAGE.md`, the figure test by running the staged check once data
   exists — and I have stated the commands rather than only the results. I did
   not add them to the tree because the dispatch asked for verification, not
   more surface.

4. **The first run of `check44` reported `D1 FAIL, D2 FAIL`** — because I ran it
   before writing the new README, which is the pre-fix state and is the reason
   the gate exists. Recorded so that the `D1 PASS` above is read as a change of
   state and not as a check that was born green.

No patch of mine silently matched nothing: every substitution in the README
writer asserts its own placeholder is present before replacing
(`assert k in out`) and asserts no `@@` survives; the `--where` block was
`bash -n`-checked and run; both staged Python files compile
(`python3 -m py_compile`).

---

## WHAT WAS FOUND

### 1. I was dispatched into a worktree four commits behind the tree my instructions described

`isolation: worktree` branched me from **`5dc7d41`**, where `main` points, not
from the session's working branch. Three things my instructions relied on are
absent here, confirmed by direct check rather than inference:

| relied on | in this worktree |
|---|---|
| `orchestration/dispatch.py --check` | does not exist |
| `proposed/ENFORCE/check42_produces.py` (gate E3) | not in the worktree. It **does** exist as untracked work in the shared checkout at `/home/user/obc-interactive/proposed/ENFORCE/`, which I read read-only; I could not run it against my tree |
| `PROTOCOL.md` R13, R14, step 4a PROMOTE | `grep` count 0. `PROTOCOL.md` here has R1–R12 and seven steps |
| `.claude/agents/build-track.md` | the older text, which says "propose changes in the audit addendum" rather than naming a staging path |

**I followed the instructions rather than the tree**, on the dispatching agent's
explicit correction: staged flat at `proposed/E/<basename>`, never
`proposed/harden/checks/…`. The flat layout was verified independently of the
missing check, with the mechanism that makes it necessary:
`python3 harden/checks/check41_machinery.py --is-protected` over all three
staged files in **both spellings**, relative and absolute, returns empty. So the
staging is correct under the definition that is actually present here, and E3's
verdict on it is unknown, not assumed.

Recorded because the failure mode is general: a subagent's brief and a
subagent's tree are two different artifacts, and nothing checked that they
agreed. Owned by **ENFORCE** (dispatch should pin the base commit, or
`dispatch.py --check` should refuse a worktree whose base lacks the rules it
cites).

### 2. A defect I am creating, and naming: H3 will read a README that no longer carries the package figures

This is not a caveat. It is a new hole, opened by my own change, and it stays
open until a human acts.

`harden/checks/check22_docs.py` is protected. In force it reads `README.md` and
requires every figure of three digits or more to appear in `FACTS.json`. After
the split the measured figures live in `PACKAGE.md`. **Until a human promotes
`proposed/E/check22_docs.py`, H3 is wrong in both directions at once**, measured
by replaying its own logic offline:

- **Green for the wrong reason.** The figures H3 exists to police — 27,421
  nodes, 3,928 bookmarks, 35,932 internal links, 25 figures in all — are in
  `PACKAGE.md`, and *H3 never opens `PACKAGE.md`*. It would pass over the file
  it was written to guard.
- **A false red.** The new README's own figures come from `data-manifest.json`,
  which is not in `FACTS.json`. Replaying the in-force figure test:
  `in-force H3 on README.md: 3 unbacked ['100', '130', '338,348,579']`. The
  338,348,579 is the manifest total; `100` and `130` are prose quoted from
  `check40`'s docstring.

The staged replacement scores each document against the source that measures it
(`PACKAGE.md` → `FACTS.json`; `README.md` → `data-manifest.json` ∪ `FACTS.json`)
and keeps the required-statement test on `README.md`. Its figure test was
exercised offline — `PACKAGE.md` 25 figures, 0 unbacked; `README.md` 8 figures,
0 unbacked; a seeded figure `41,234,567` caught in both — but the check **as a
whole cannot be run here**, because its first action is `subprocess.run(gen_readme,
check=True)` and `gen_readme` opens `emitters/obc.sqlite`. It is reviewed, not
verified, and its docstring says so. Owned by **track E, item E9**, and it is
not closed.

### 3. The most recent fix to the verification machinery is in no audit revision

`harden/checks/check41_machinery.py` carries a `git update-index --refresh`
before `git diff-index`, and a second, false-positive half to its negative
control, because `diff-index` compares cached stat data: a file whose `mtime` or
`ctime` moved with its content byte-identical was reported as modified, and
**CI run 11 turned E2 red with nothing changed**. `ci/test_hooks.sh` moves
`_cmdstrip.py` and `check41_machinery.py` out and back, which is enough to do
it. It passed locally only because an interactive session runs `git status`
constantly, which refreshes the index as a side effect — so the bug was
invisible in exactly the environment it was developed in.

All of that is in the source comment and in commit message `5dc7d41`.
**`grep -rn "mtime" AUDIT*.md` returns nothing.** It is in no revision, and my
own brief cited AUDIT-rev13.md for it — rev13 is about the workflow guard and
the protected set, and does not mention it. The commit post-dates rev13.

So the project's own record has a gap of exactly one commit, at the check that
guarantees every other check has not been tampered with, and the gap was
propagated into a dispatch brief as a citation to a document that does not
support it. Owned by **ENFORCE**. The finding it should have recorded is worth
stating in its own right: *a false red gets a gate ignored as thoroughly as a
false green*, and it is the reason both of DOC1's controls assert both
directions rather than only the mutation.

### 4. The split, taken literally, would have turned G16d and H3 red

The brief said `PACKAGE.md` takes the completion table. That table is the only
place `README.md` says **`HANDOFF REQUIRED`** and **`E4`** — and both
`verify/emitters/checks/check19_package.py:87` (G16d) and
`harden/checks/check22_docs.py` (H3) assert those phrases **against
`README.md`**. Moving the table wholesale drops them, and two gates go red on
their required-statement assertion for a reason that has nothing to do with what
either gate is about.

Nothing cross-references this. Neither check mentions the other; the phrase
lists differ (`current to` in H3 only, `E4` in G16d only); and the constraint is
discoverable only by reading a line in a check that runs against a zip built
from data this clone does not have. The measured table moved as instructed; a
short prose statement of the same handoff, naming `HANDOFF REQUIRED` and `E4`,
stayed on the front page, where a reader needs it anyway. The constraint is now
mechanical: `check44_distribution.py --statements` → 6 of 6 present, with the
owning gate named per phrase.

Owned by **track E, item E9**. The wider point belongs to whoever next edits the
front matter: **two gates assert content against one file and neither knows the
other exists.**

### 5. One quantity, three typed figures, none measured

The derived data is **338,348,579 bytes**, from `data-manifest.json`. Around it:

| location | says | actual |
|---|---|---|
| `.gitignore:20` | `315 MB` | 338.3 MB (`/1e6`), 322.7 MiB |
| `.gitattributes:9` | `315 MB` | same |
| `ci/fetch_data.sh:4` | `~323 MB` | 322.7 **MiB** — right number, wrong unit |
| `harden/checks/check40_dataintegrity.py:95` | prints `(323 MB)` from `total_bytes/1048576` | divides by 2²⁰ and labels it MB |

`315` is wrong by 23 MB against the manifest and is typed in two places. `323`
is MiB called MB, and it is *printed by a check*, which is how it acquired
authority. This is R9 — documentation is measured, not typed — in the three
files that exist to explain why the data is absent. The new `README.md` states
`338,348,579` and takes it from the manifest at write time; the other four are
untouched and are the finding. Owned by **MAINT** if the fix is to correct the
strings; owned by **E** if the fix is to make `check40` print both units and the
other three stop repeating a number they do not measure.

### 6. Two smaller ones, stated rather than filed

- **D1 is vacuous on a hydrated tree.** An assertion quantified over "every
  absent file" cannot fail when nothing is absent — R4, one level up from where
  R4 was written. The check does not print a bare `PASS` in that case; it prints
  `D1 vacuous (nothing absent)`. Naming a vacuous pass in the output is the
  cheapest thing this project has learned and it is not free: someone has to
  write the branch.
- **`guard-machinery.sh` refused two of my shell commands for the keyword, not
  the effect.** A `python3` heredoc that only read files, and a `sed` whose
  *replacement string* contained a well-known code-hosting hostname, were both
  refused as "names git in a form too complex to verify". Neither touched a
  repository. This is the guard erring in the safe direction, exactly as
  `check41._candidates()` documents for suffix over-matching, and I record it
  as observed behaviour rather than as a defect: the cost is an executor
  rephrasing a command, and the alternative cost is a write into the main
  checkout from a worktree. Owned by **ENFORCE** if anyone ever wants to
  measure the false-refusal rate.

---

## Tally

**7 of ~31 items done, unchanged — plus one new item registered (E9), so ~32.**
Nothing completed this pass. E9 is *built and named*, not done: DOC1-D2 is red
by design, PROTOCOL steps 5 and 6 are unreachable on a clone with no data, and
three files sit staged in `proposed/E/` awaiting a human.

From `python3 orchestration/schedule.py`: **READY (4)** — A4, C, E, MAINT;
critical path `A4 → B → G → FSCOPE → FOBJ → FRULES`, ~17 weeks.

**Immediate next action:** promote the three files in `proposed/E/` — most
urgently `check22_docs.py`, because H3 is measuring the wrong file from the
moment this change lands and every run of the board between now and then is
green on H3 for a reason that has stopped being true. Then publish the data
release and turn DOC1-D2 green; it is the only thing on this list that no
executor can do.

---
Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the
official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.

---

# Orchestrator's section — the first wave, and what running agents found that reading could not

Appended by the orchestrating session, 2026-09-08. Everything above is the E9 subagent's own audit, preserved.

## The wave

Two `build-track` agents, dispatched as one wave under `dispatch.py`'s plan.

| track | wall-clock | segments | tool uses | outcome |
|---|---|---|---|---|
| MAINT | 20m 10s | 2 (14:55 + 5:15) | 101 | steps 1–4a; 5–6 blocked on data |
| E / E9 | 32m 44s | 2 (12:38 + 20:06) | 171 | steps 1–4a; 5–6 blocked on data |

**`agent_effort` stays `unmeasured` on both**, and that is the mechanism working rather than a disappointment. The field's definition is wall-clock to a *verified board*; neither run reached one, and neither agent claimed otherwise — MAINT volunteered *"I ended with a red board… M1 and M2 are not established"* without being asked. The figures above are recorded here, in prose, precisely because they are not what `agent_effort` means. Writing 20 minutes into that field would be the "~17 weeks" defect committed by a different hand.

Verified on the reconciled tree rather than taken from the agents: E3 PASS, `schedule --check` PASS, `dispatch --check` PASS, DOC1 D1 PASS / D2 FAIL, MAINT's `check45` PASS on fixtures, E1 PASS, E2 PASS.

## WHAT BROKE — three defects in the orchestration layer, all found by running it

### 1. `isolation: worktree` branches from the default branch, not from HEAD

Both agents were placed on **`5dc7d41`**, where `main` points, not on the working branch. `git merge-base --is-ancestor` says `9380139`, `bda3de9` and `e427e49` are all ABSENT. So each was briefed to operate machinery its tree did not contain: no `dispatch.py`, no `check42_produces.py`, no R13/R14/step 4a in `PROTOCOL.md` (grep count 0), and the older `build-track.md` without the staging instructions.

**It looks like it worked, which is what makes it dangerous.** MAINT staged correctly under `proposed/MAINT/`, wrote `promotes:` entries, and renamed its check to avoid a collision — all from the dispatch prompt, none from the repository. A reader of its output would conclude the conventions were enforced by the tree. They were carried by a prompt, and a prompt is not a mechanism (R11). It also reported running `dispatch.py --check`, which cannot be true.

The regression it would have caused: the stale `tracks.yaml` is the pre-`9380139` schema, so merging either worktree reverts `human_effort`, `agent_effort`, `human_gate`, `serialises_on` and every `promotes:` block **for all fifteen tracks**, through a clean merge with no conflict. `integrate-track`'s pre-merge `check41` cannot see it: `tracks.yaml` is deliberately unprotected, because tracks must update their own status. And a stale merge reverts the checker and the checked in one commit, so detection must live under `harden/checks/` and run from the main checkout. **Neither worktree was merged.** Both were reconciled file by file, and each track's `tracks.yaml` contributions were ported by hand onto the current schema.

Remedy staged in four ordered steps at `proposed/ENFORCE/worktree-base.md`, with the both-halves control it needs.

### 2. `guard-commit` refuses every commit while a subagent is live

`guard-commit-and-corpus.sh:26` excludes `.git`, `__pycache__`, the stamp, `gate-board.json` and two `out/` trees — not `.claude/worktrees/`, where `isolation: worktree` puts a full checkout per agent. Observed twice: at 18:49 on a worktree `tracks.yaml`, then at 18:51 after refreshing the stamp *immediately* before committing, on a `tools/fixtures/.gitignore` the agent created in the gap.

The second observation is the one that matters. There is no ordering of touch-and-commit that beats an agent still working, so while a wave runs, commits on the main checkout are refused — which breaks the review-gate-per-wave model adopted two commits earlier. The commit that eventually landed did so because an agent happened to be idle for a moment. That is luck, not a fix. Patch staged with the two E1 cases it owes, the second being the control that stops the exclusion being widened to everything.

### 3. `maxTurns: 60` cuts every track mid-cycle

Both agents hit the ceiling, on tracks scoped to steps 1–4a alone; both needed a resume; MAINT took 101 tool uses and E9 171. The seven-step protocol does not fit in 60 turns for a real track, so **every dispatch needs a resume, and a resume is a decision point a human must be present for** — silently converting "human gate per wave" into "human gate per agent segment", the opposite of the wave model's purpose.

The sharper half is *where* it cuts. MAINT stopped after building and before verifying, so its self-report named a check it had never run. An agent that stops between those two steps is indistinguishable from one that finished. Raising the number is the small fix; building the resume into `dispatch.py` rather than into the orchestrator's attention is the real one.

## WHAT WAS FOUND — the audit trail forked

`AUDIT-rev14.md` existed twice: 121 lines committed on the branch, 375 lines untracked in the E9 worktree, both titled *Track audit — revision 14*. The subagent numbered correctly for the tree it could see, where the highest revision is 13. Renumbered to 15 here with a note in its own header; its text is otherwise unedited, per R10.

This is worth more than an inconvenience. R10 exists because an audit that retouches its own past is a status report. A stale-base dispatch does not retouch the past — it **forks** it, producing two documents with equal claim to the same number and no marker saying so. Nothing in the repository would have detected it; it was found by listing a directory.

## WHAT DID NOT

No track moved. **7 of ~31.** MAINT and E both stay `ready`; `verify-track` certifies `done`, and it has not run — on a data-less clone its own contract makes it report UNVERIFIED, never PASS.

DEC1–DEC4 unanswered. DOC1-D2 red by design. DATA1 red, 29 files. `agent_effort` unmeasured on all ten open tracks. The regenerate owed by rev14 is still owed, and this commit adds to it — the same authorised `guard-commit` bypass, which here also steps over defect 2 above.

## Tally and next action

1. **Pin the dispatch base commit before any further wave.** A stale-base dispatch that appears to succeed is worse than one that fails loudly, and this one surfaced only because a byte count in a subagent's report did not look right.
2. Promote, in this order: `proposed/ENFORCE/check42_produces.py` (E3), `proposed/E/check22_docs.py` (H3 reads the wrong file from the moment the split lands), then the rest.
3. Publish the data release. It is the only action that closes DOC1-D2 and DATA1 together, retires the commit bypass by making `ci/regenerate.sh` a real run, and lets `integrate-track` merge instead of correctly refusing.
4. Then dispatch one track end to end and write the first real `agent_effort`.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
