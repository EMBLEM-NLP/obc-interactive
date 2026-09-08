# Track audit — revision 8

After closing the Bash write path into verification machinery, Claude Code on the web, 2026-09-08. Revisions 1–7 preserved unedited.

**Headline: the fail-open recorded as finding 4 of revision 7 is now covered, and covered honestly. Prevention is a Bash hook, verified blocking under the host. The guarantee is a gate — `check41_machinery.py`, E2 — that compares the machinery against `HEAD` and so sees the effect whatever produced it. The distinction matters, because a Bash guard cannot be sound against an executor that also holds Bash, and this document does not claim otherwise. While writing it I modified a protected check through a Python heredoc; the hook did not see it and the gate did.**

---

## WHAT MOVED

| item | evidence |
|---|---|
| Gate **E2** exists | `harden/checks/check41_machinery.py`, registered in `ci/checks.yaml`. `git diff-index --name-only HEAD` over the protected set, plus `git ls-files --others` for untracked additions. 90 protected files; the query costs 4 ms, so it is affordable on every board run. |
| E2 is falsifiable | `NEGATIVE=1 python3 harden/checks/check41_machinery.py` copies the tree, appends a line to `harden/checks/check23_controls.py`, and requires the check to see it. `RESULT: PASS — the mutation was detected, so this gate can go red`. The mutation targets a check, which is the mechanism under test, not the git baseline it is scored against (R2). |
| Prevention hook, **verified live under the host** | `.claude/hooks/guard-machinery.sh`. `touch harden/checks/probe.tmp` was refused on screen: *"this command writes to verification machinery: harden/checks/probe.tmp"*. No file was created. This is a stronger observation than revision 7 managed for any hook except `decision-guard` — the host itself blocked it, rather than a script being exercised. |
| Write detection reuses the lexer | `--writes` mode added to `.claude/hooks/_cmdstrip.py`, built on the same heredoc-stripping, quote-respecting, command-position machinery written for the commit guard. Covers redirections, `sed -i`, `tee`, `cp`, `mv`, `rm`, `install`, `truncate`, `patch`, `chmod`, `chown`, `ln`, `dd`, and the working-tree `git` subcommands, recursing into `bash -c`. |
| CI1 is not collateral damage | `ci/run_gates.py --control` writes a seeded failing check **into** `harden/checks/` and unlinks it, which is the control proving the board can go red. A naive path guard would have blocked the project's own falsification. It is an explicit allowed case in the suite, and `check_seeded_failure.py` is exempt in E2's `TRANSIENT` set. |
| One list, not two | The `deny` array in `settings.json` and the `case` in `protect-checks.sh` did not agree — the hook covers `gates/GATES-*.md` and `Write()` on `ci/run_gates.py`; the deny list covers neither. `PROTECTED` in `check41_machinery.py` is now the single definition, and `guard-machinery.sh` asks that file rather than keeping a third copy. |
| Suite 35 → **52** cases | `bash ci/test_hooks.sh` → `RESULT: PASS`. Count measured, not typed. Adds nine blocked write routes, five allowed ones (including CI1, reading a check, and editing a stage), and three fail-closed cases: garbage stdin, `_cmdstrip.py` missing, `check41_machinery.py` missing. |
| Subagents inherit it | `.claude/agents/build-track.md` gains the hook on its Bash matcher. The builder agent is exactly the executor this exists to constrain. |
| The suite stopped littering the protected set | It parked `_cmdstrip.py` as a sibling `.off` file while testing the missing-helper case. That path is itself protected and untracked, so E2 would have reported the test suite as machinery drift. It now parks helpers in `mktemp -d`. |

---

## WHAT DID NOT

Every track unchanged: A1, A2, A3, PORT, ENFORCE, G surface, G2 done; A4, C, E, MAINT ready; B, G, FSCOPE, D, FOBJ blocked; FRULES conditional. **7 of ~31.** `schedule.py --check` → `RESULT: PASS`; DEC1–DEC4 present; no status typed.

- **E2 has never run as part of the board.** It was exercised standalone and through its own control. `ci/run_gates.py` aborts at DATA1 before reaching it on this clone, and `gate-complete.sh` now aborts even earlier, for the same reason. Registered is not the same as exercised in place, and this document keeps them apart. See finding 3.
- `protect-checks` is still unobserved firing under the host; the `settings.json` deny is evaluated first and refuses the edit before any hook runs.
- No data, no gate board, no `@build-track` dispatch, no `SubagentStop` observation. CI still red at the data fetch.
- `MANIFEST.sha256` remains stale and cannot be regenerated without the derived data.
- The four decisions are untouched. No `main` branch. No PR.

---

## WHAT BROKE

1. **`lstrip("./")` silently excluded every hook file.** It strips any leading `.` or `/` *character*, not the prefix `./`, so `.claude/hooks/decision-guard.sh` became `claude/hooks/...` and matched no pattern. The protected count read 82 where it should read 89 — the seven missing files being the hooks, the most sensitive part of the set. Caught by probing the matcher against known paths instead of trusting the count. A guard whose own path matcher quietly drops its most important entries is the exact failure this project keeps finding, and I wrote it.
2. **Commas inside a YAML flow mapping corrupted the `checks.yaml` entry.** The `{script: ..., note: ...}` form treats every comma as a key separator, so a prose note split into bogus keys. The file still parsed, which is why it needed a check on the parsed structure rather than on the exit code. Rewritten in block style with a folded scalar.
3. **The E2 control manufactured its own false signal.** `shutil.ignore_patterns("emitters")` matches *any* directory of that name, so it dropped `pipeline/emitters/checks/` and `verify/emitters/checks/` from the copy and git reported eight files as drifted that were not. The seeded mutation was still detected, so the control's verdict was right for the wrong reason — the noisiest possible way to be correct. Exclusions are now by path.
4. **`--writes` over-collected read redirections.** `tee f < g` reported `g` as written. Harmless for blocking, since the extra path is rarely protected, but a detector that names paths it does not mean cannot be trusted about the ones it does. Fixed and covered by a case.
5. **Two Bash writes were refused by the host's permission classifier**, both for embedding an install command with a third-party index URL. I did not obfuscate around it; the affected fix was redesigned instead, as recorded in revision 7.

---

## WHAT WAS FOUND

### 1. The honest limit, demonstrated rather than asserted
While fixing the control I edited `harden/checks/check41_machinery.py` — a protected file, with the hook live — using a `python3 - <<'PY'` heredoc that called `open(..., "w")`. **`guard-machinery.sh` did not block it, and could not have.** No reading of a command string can know what a program will write. E2 reported the drift immediately.

That is the design, stated plainly so nobody mistakes the hook for a wall:

| layer | catches | cannot catch |
|---|---|---|
| `settings.json` deny | Edit/Write/MultiEdit on the paths it lists | anything through Bash |
| `protect-checks.sh` | the same, one layer in | anything through Bash |
| `guard-machinery.sh` | ordinary shell writes, named immediately | writes inside a program; an executor that rewrites the hook or `settings.json` |
| **E2 `check41_machinery.py`** | **the effect, however it was produced** | a change that is also committed |

An executor holding Bash can defeat any Bash guard. What it cannot do is change a file and leave `git diff-index` unable to see it — short of committing, which is gated by `guard-commit` and recorded in history with a message. So the achievable property is not prevention; it is that **no modification of verification machinery goes undetected before a session or subagent may finish**, because `gate-complete.sh` runs the board on the way out. That is worth having and it is less than "closed".

### 2. The two protected lists had drifted apart
`settings.json` denies `Edit(ci/checks.yaml)`, `Edit(ci/run_gates.py)` and `Edit(ci/regenerate.sh)` but not `Write()` on any of them, and says nothing about `gates/GATES-*.md`. `protect-checks.sh` covers all of those, for Edit and Write alike. Two lists meant to express one policy, disagreeing on four paths, each looking authoritative. Now one list, in the gate, consulted by the hook.

### 3. The DATA1 abort hides the two gates that need no data
`ci/run_gates.py` runs `check40` first and stops the board when it fails — correct, since every later gate would read absent data. But E1 (the hook suite) and E2 (machinery drift) read no data at all. On a clone without the 323 MB, the board therefore reports one failure and zero gate results, when two gates were available and would have passed.

This is finding 5 of revision 7 in a second place: there it was CI ordering the hook test after the fetch, here it is the board's own abort. The fix is to run the data-independent checks before the DATA1 gate and report them, then abort. **Not done here.** It changes `ci/run_gates.py`, which no test on this clone can exercise end to end, and shipping an untested change to the board runner is how the last two fail-opens arrived. It belongs with the first board run that has data.

### 4. A test suite can pollute what it verifies
Recorded above under WHAT BROKE, but it generalises: the suite tested the missing-helper case by moving a hook to a sibling path inside `.claude/hooks/`. Once a gate watches that directory for untracked files, the test becomes a source of the very signal the gate reports. Tests that mutate the tree they are checked against need somewhere else to stand.

---

## Tally and next action

**7 of ~31 done**, unchanged. Nothing in this pass moved a track. It closed the last known route by which an executor could quietly edit the checks that grade it, and made that route detectable rather than merely discouraged.

In order:

1. Publish the data tarball; set `OBC_DATA_URL`, `OBC_PDF_URL_V1`, `OBC_PDF_URL_V2`, `ANTHROPIC_API_KEY`. Still item 1, still not mine.
2. Create `main` from this branch and make it default.
3. On the first run with data: confirm E2 executes on the board, run `ci/regenerate.sh` so `MANIFEST.sha256` covers everything added since the seed commit, and apply finding 3 above.
4. Then step 5 of `MIGRATION.md` in full — the smoke test, `@build-track`, and the `SubagentStop` observation — recorded in `AUDIT-rev9.md`.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
