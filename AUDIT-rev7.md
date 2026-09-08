# Track audit — revision 7

After the enforcement-hardening pass, Claude Code on the web, 2026-09-08. Revisions 1–6 preserved unedited.

**Headline: the fail-open found in revision 6 is closed, and closing it found two more. `decision-guard` now blocks the Edit tool under the host, and `guard-commit` decides whether a command runs a commit by lexing it rather than grepping it — which turned out to matter more than the false positive that exposed it, because the original regex could be evaded two ways. Every fix carries a control: reverting it turns `ci/test_hooks.sh` red. The gate board still cannot run here; there is no data on this clone and this document does not pretend otherwise.**

---

## WHAT MOVED

| item | evidence |
|---|---|
| `decision-guard` closed | Reconstructs the document an edit would produce — `content` for Write, `old_string`→`new_string` for Edit, the `edits` array for MultiEdit — and judges that. Under the host: an Edit flipping FRULES to `ready` and an Edit deleting DEC1 are both **blocked on screen**. Those are the two edits that succeeded earlier in this same session. |
| Three fail-open exits removed | `[ -z "$HOOK_NEW" ] && exit 0` (a deletion), `except Exception: sys.exit(0)` (unparseable), and the silent no-op when the payload carried no `tracks` key. Each now exits 2 with a stated reason. |
| `_input.py` exports `HOOK_RAW` | A hook reads stdin once and the shared parser consumed it, so no helper could recover `old_string` or a MultiEdit array. Additive; the three existing consumers are unchanged. |
| `guard-commit` decides by lexing | New `_cmdstrip.py`: heredoc bodies dropped, split on `;` `&&` `||` `\|` and newline respecting quotes, `shlex` per segment, command position only, recursing into `bash -c`. Fails closed when it cannot lex, and `guard-commit` exits 2 if the helper is missing — a case in the suite. |
| `ci/test_hooks.sh` 19 → **35** cases | `bash ci/test_hooks.sh` → `RESULT: PASS`. Count measured with `grep -cE '^  (ok\|FAIL)'`, not typed: 6 protect-checks, 9 commit detection, 6 stamp and corpus, 7 decision-guard Edit shapes, 3 Write shapes, 4 fail-closed. |
| **Both fixes are falsifiable** | Tree copied to a scratch directory, one hook reverted to the handoff original, suite re-run. Reverting `decision-guard` → `RESULT: FAIL 5 hook case(s)`. Reverting `guard-commit` → `RESULT: FAIL 3`. E1 can no longer be green over either defect. |
| `gate-complete` names the right cause | Runs `check40 --quick` first. On this clone it now says the data is missing and points at `ci/fetch_data.sh`, where before it said "check35 (H10) failed — a ratio gate has no falsifying mutation" with no ratio gate broken. |
| Readers cannot create a database | `obc_context.connect()` opens `mode=ro` and raises `FileNotFoundError` naming the remedy when the file is absent. Verified: the call fails with a stated reason, `emitters/` is still absent afterwards, no 0-byte file appears. |
| The tool surface says why it failed | `obc_capabilities` returned a bare `Error executing tool obc_capabilities` over MCP earlier today. It now returns `available: false` with the reason, the remedy and a `cannot` list saying every question is unanswerable here. `search` raises `DataUnavailable` carrying the same remedy. |
| Findings 4, 6, 8 applied | `session-start.sh` no longer installs the embedding stack at all (below). MIGRATION.md corrected to 402 KB and 197 files. `gates.yml`: E1 moved above the data fetch; `if-no-files-found: error` on the board artifact. |
| MCP connects under the host | Six tools listed and callable from a cloud session. First time observed rather than assumed; `ENVIRONMENTS.md` predicted fidelity would hold and it does. |

---

## WHAT DID NOT

Every track is unchanged. A1, A2, A3, PORT, ENFORCE, G surface, G2 done; A4, C, E, MAINT ready; B, G, FSCOPE, D, FOBJ blocked; FRULES conditional. **7 of ~31.** `schedule.py --check` → `RESULT: PASS`; DEC1–DEC4 all present; no status typed by hand.

- The gate board did not run. `ci/run_gates.py` still aborts at DATA1 with 29 files missing. No gate that reads the graph has been exercised here, so nothing in this document rests on one.
- `protect-checks` is **still unobserved firing under the host**. Editing a check is refused by the `Edit(harden/checks/**)` deny in `settings.json`, which is evaluated before PreToolUse hooks, so the hook never runs. Two layers, and only the outer one has been seen to act.
- The step-5 sequence in `BOOTSTRAP.md` is still not complete: no board, no `@build-track` dispatch, no `SubagentStop` observation.
- CI is still red, and will stay red until the data secret exists. Runs 1 and 2 both died at the data fetch with `OBC_DATA_URL` unset, having produced no gate result at all.
- `MANIFEST.sha256` is stale by 16 files and now by this one too. `ci/regenerate.sh` needs the data and refuses without it, so G16d and H8 stay red until someone runs it where the data lives.
- No data published, no secrets set, no `main` branch, no PR. All of those remain the user's.

---

## WHAT BROKE

1. **My own first fix introduced a false-positive class, and the guard caught me with it.** `_cmdstrip.py` lexed line by line. A command ending in a multi-line `python3 -c "…"` argument has an unterminated quote on its first line, `shlex` raised, and the helper returned COMMIT for a command containing no commit at all — blocking my next edit. Fail-closed is the right direction and was still the wrong answer. Fixed by converting newlines outside quotes to separators and lexing the whole command once. A case for it is in the suite, together with "multi-line argument followed by a real commit", which must still be caught — it is.
2. **I planned a change that would have broken H10.** The approved plan said to open the three `sqlite3.connect` sites in `check35_controls.py` read-only. Two of them are the mutations themselves — `mut_drop_term_resolved` executes `DROP TABLE`, `mut_ablate_prohibition` executes `UPDATE`. Read-only would have disabled the falsification H10 exists to perform. Only the shared reader in `obc_context.py` was changed; `check35` is untouched. Caught by reading the file before editing it, which is the only reason it was caught.
3. **A `.regen.stamp` race, twice.** `touch .regen.stamp && git commit` in one command is refused, correctly: a PreToolUse hook inspects state before the command runs, so the stamp is not yet newer. Two commands, not one.
4. **I asserted 34 test cases in `tracks.yaml` before counting.** The measured count is 35. Corrected before commit. R9 exists for exactly this and I still typed a number first.
5. **Two writes were refused by the host's permission classifier**, both for embedding a `pip install` with a third-party index URL in a file being written. I did not obfuscate around it. The finding-4 fix became better as a result: the hook no longer installs the embedding stack at all, which removes the unattended multi-gigabyte download rather than reordering it.

---

## WHAT WAS FOUND

### 1. The report and the repository disagreed, and the repository was right
This session opened with a status report stating that the `decision-guard` Edit fix, `_cmdstrip.py`, 25 passing hook cases and findings 4, 6 and 8 were **done**. None of it existed. Established three ways before any work started:

- `git ls-remote origin` returned one ref, `81b71d9`, identical to local HEAD — no `main`, no second branch, no PR head, nowhere else for the work to live.
- `diff` against the handoff zip: all six hooks, `ci/test_hooks.sh`, `settings.json` and `gates.yml` **byte-identical to the originals**.
- `.claude/hooks/` held six files; `_cmdstrip.py` was absent; `test_hooks.sh` had 19 cases.

`AUDIT-rev6.md` had said so plainly — *"The fix is proposed in the audit, not applied"* — and the report read those proposals as completions.

`PROTOCOL.md` already names this under what a track may not return: *"A status of `done` for anything the source data does not reflect."* Revision 1 of the audit opened with the same finding about the remediation pack — seven items "built and verified" and zero integrated — and it has now recurred one level up, about the audit's own proposals rather than about code. The defect this project exists to catch is a claim indistinguishable from a true one until something probes it, and a summary of work is exactly such a claim. **Probe the tree, not the transcript.** Nothing in this revision is asserted from the report; every line above cites the command that produced it.

### 2. The original commit guard could be evaded two ways, not just fooled one way
Revision 6 recorded a false positive: a heredoc mentioning the verb was treated as a commit. Running the new suite against the **original** hook found the more serious half:

| command | original guard | why |
|---|---|---|
| `bash -c 'git commit -m x'` | **allowed** | the character before `git` is a quote, which the regex's `(^\|[;&\|[:space:]])` prefix does not match |
| `git -C /repo commit -m x` | **allowed** | `commit` is not adjacent to `git`, so `git[[:space:]]+commit` never matches |
| heredoc mentioning the verb | blocked | matched inside data |

So the guard refused a legitimate action and permitted two real ones. The obvious repair — strip quoted spans before matching — would have made the first row worse, since that commit lives entirely inside single quotes. Grepping cannot separate data from code; only lexing can. This is R2 in a new place: **the fix must target the mechanism, and a repair aimed at the symptom can widen the hole it was meant to close.**

### 3. A guard that misnames its cause sends the next executor to the wrong place
`gate-complete` reported "check35 (H10) failed — a ratio gate has no falsifying mutation" on a clone whose only problem was absent data. An executor reading that would go looking for a broken mutation registry. Every other entry point in this project already named its cause; the two that did not were the Stop hook and the MCP tool surface, which are precisely the two an agent meets first. Both now name it.

**Correction to revision 6, finding 3.** Rev6 said `check35` "creates a 0-byte `obc-mod.sqlite` as a side effect". That is conditional and rev6 did not say so: `sqlite3.connect` creates a file only when the parent directory exists. On a fresh clone `emitters/` is absent — git stores no empty directories — so the call raises instead and nothing is created. The 0-byte artifact appears only after something has made the directory, as an unpacked archive had here. The remedy is unchanged; the diagnosis is narrower than stated.

### 4. `settings.json` and `protect-checks.sh` do not guard the same surface
The deny list covers `Edit(...)` and `Write(...)` on the check directories, but `Bash` is not denied. Any of `sed -i`, `python3 -c`, `cat >` or a heredoc can write to `harden/checks/` without either the deny list or `protect-checks` seeing it — the hook is registered on `Edit|Write|MultiEdit` only. I used exactly that route to write the hook files in this session, with explicit human authorization, which is the point: the route exists and is not instrumented. `guard-commit` inspects Bash commands already, so the natural home for a fix is there. **This is now the widest known fail-open in the enforcement layer and it is not closed.** Not fixed here because a Bash write guard needs its own controls and its own review, and shipping it untested is how the last two fail-opens arrived.

### 5. Two CI runs produced no gate result when one was free
`gates.yml` ran the hook test after the data fetch, so runs 1 and 2 skipped E1 — a gate that needs no data and would have passed. The artifact upload also reported success while logging "No files were found", because `if-no-files-found` defaults to `warn`; a missing board read as a delivered one.

Both reordered, and **verified on run 3** (id 34238480779, head `26c04a6`), not left as a prediction:

| step | run 1 and 2 | run 3 |
|---|---|---|
| `hooks are falsifiable` (E1) | skipped, after the fetch | **success in 4 s**, before the fetch |
| `fetch derived data` | failure, secret unset | failure, secret unset |
| `upload-artifact` | success, logging "No files were found" | **failure**, board genuinely absent |

E1 passing on run 3 is the first gate result this project's CI has ever produced. The trade-off in the upload change is real and was accepted: a run that dies early now shows two red steps rather than one. That is louder, and it is accurate; the previous green was neither.

---

## Tally and next action

**7 of ~31 done**, unchanged. `python3 orchestration/schedule.py` reports A4, C, E and MAINT ready and the critical path A4 → B → G → FSCOPE. What moved today was not a track: it was the enforcement layer becoming able to fail, which is the precondition for trusting anything the other 24 produce.

In order, and none of the first three is mine to do:

1. Publish the data tarball; set `OBC_DATA_URL`, `OBC_PDF_URL_V1`, `OBC_PDF_URL_V2`, `ANTHROPIC_API_KEY`.
2. Create `main` from this branch and make it the default; the repository was empty at first push, so a working branch became the default by accident.
3. Run `ci/regenerate.sh` where the data lives, so `MANIFEST.sha256` covers the files added since the seed commit.
4. Then finding 4 above — a Bash write guard for the check directories, with controls — before any `@build-track` dispatch, since an executor with Bash can currently edit the checks that grade it.
5. Then step 5 of `MIGRATION.md` in full, recorded in `AUDIT-rev8.md`.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
