# Track audit — revision 13

CI reaches DATA1; the workflow joins the protected set. Claude Code on the web, 2026-09-08. Revisions 1–12 preserved unedited.

**Headline: a research document proposed guarding the data fetch on a secret so an unconfigured build fails at DATA1 rather than at the fetch. Its GitHub Actions research is sound and its drop-in block would not have worked, because `ci/regenerate.sh` sits between the fetch and the board and refuses without data — skipping the fetch moves the failure one step later without ever reaching DATA1. Guarding both is the fix. Auditing it also turned up that the workflow which runs the board was not protected while the runner it invokes was, and that a claim in revision 10 was overstated.**

---

## WHAT MOVED

| item | evidence |
|---|---|
| `gates.yml` guards the fetch | Job-level `env.HAS_DATA` computed from `secrets.OBC_DATA_URL != '' \|\| secrets.OBC_DATA_TARBALL != ''`. Job-level `env` may read `secrets`; a step-level `if:` may not — referencing `secrets` there is a parse-time rejection of the whole workflow, not a false-y evaluation. |
| **and guards `regenerate` too** | The document's gap. `bash ci/regenerate.sh` exits 1 without data — run live: *"Refusing to regenerate — a manifest built now would describe a tree that does not exist."* It sits between the fetch and the board, so without this guard the board stays skipped and DATA1 never runs. |
| `OBC_DATA_TARBALL` now passed | `ci/fetch_data.sh` accepts tarball, dir or url; the workflow passed only the url. |
| DAG consistency moved above the fetch | `orchestration/schedule.py --check` reads only `tracks.yaml`. It sat after the fetch and was skipped in all ten runs to date, for want of data it never touches. Same reasoning as E1 in `2ba87fc`, and as `no_data:` in `ci/checks.yaml`. |
| A skipped fetch is legible | `::warning::` plus a `$GITHUB_STEP_SUMMARY` block. Annotations never change a conclusion, which is the point: the run stays red and says why. |
| `.github/workflows/*` protected | Protected files 94 → 95, delta verified as exactly `.github/workflows/gates.yml`. `guard-machinery` and gate E2 now cover the workflow that runs the board, as they already covered `ci/run_gates.py` and `ci/checks.yaml`. |
| `protect-checks.sh` consults `PROTECTED` | Its own `case` statement is gone. One definition, three consumers. |
| `ci/test_hooks.sh` 71 → **77** | `RESULT: PASS`. Six new cases: Edit and Bash writes to the workflow refused by both hooks, absolute-path form refused, `.github/ISSUE_TEMPLATE.md` and `schema/` still allowed. |

---

## WHAT DID NOT

Every track unchanged. **7 of ~31.** DEC1–DEC4 present; FRULES conditional.

- **The expression syntax is unverified until the run.** Nothing here can execute GitHub's evaluator. The next push is the test, and its three outcomes are all informative: a parse error means the form is wrong and it reverts; the fetch showing *skipped* with the board reaching DATA1 means it worked; the fetch still failing means `HAS_DATA` did not evaluate as expected.
- **Two behaviours cannot be checked from here at all**: a run with the secret actually set, and a fork pull request. On a fork, secrets are withheld and resolve to empty, so the guard should skip the fetch and DATA1 should still fire red — the no-false-green property, worth confirming once data exists.
- The board still reports `DATA1 FAIL` locally. Nothing about this pass makes a gate pass; it makes more gates *run*.
- The document's second recommendation — never let the board job itself become skippable, because a skipped job reports success to required checks — was already satisfied and stays that way. No job-level `if:`, no `continue-on-error`.

---

## WHAT BROKE

1. **My method for checking the protected-set delta was broken, and it accused the wrong thing.** I copied `check41_machinery.py` to a scratch directory to run the HEAD version alongside the new one. `_PKG` is derived from `__file__`, so the copy resolved its package root to a directory that is not a git repository, `git ls-files` returned nothing, and the diff reported all 95 files as newly protected. Recomputed properly against `git ls-files` with and without the new pattern: the delta is exactly one file. A verification that fails for its own reasons is worse than none — this is the second time in two revisions I have written one, after the README row check that counted the digits in `volume1`.
2. **Revision 10 overstated a fix of mine.** It said `PROTECTED` in `check41_machinery.py` "is now the single definition of verification machinery, replacing two lists that disagreed". It replaced one: `guard-machinery` consulted it, but `protect-checks.sh` kept its own `case` statement, so there were still two. The drift showed immediately — adding `.github/workflows/*` to `PROTECTED` would have left `protect-checks` alone in still permitting an Edit on the workflow. Now genuinely one definition with three consumers. The correction lives here; revision 10 stays unedited.

---

## WHAT WAS FOUND

### 1. Three claims in the proposal do not describe this repository
The document's GitHub Actions research is accurate as far as I can judge, and its ranked alternatives are well-reasoned. Its claims about *this* repository are another matter:

| claim | actual |
|---|---|
| It critiques a proposed guard `if: ${{ secrets.OBC_DATA_TARBALL != '' \|\| secrets.OBC_DATA_URL != '' }}` | **No `secrets`-in-`if:` exists anywhere in the workflow.** The only two conditions are `always()` on the artifact upload and `github.event_name == 'pull_request'` on the summary step. Nobody proposed it here. |
| "your Run #9 (a same-repo-branch PR)" | **All ten runs are `push`.** Filtering by `event: pull_request` returns `total_count: 0`, and no pull request has ever existed on this repository. |
| "Downstream steps need no `if:` … so `ci/run_gates.py` executes" | **False here.** `ci/regenerate.sh` fails between the fetch and the board. |

The third matters most, because it is the difference between a fix that works and one that relocates the symptom. A document can be right about the platform and wrong about the tree, and the parts that are checkable locally are the parts worth checking — the rest is verified by the run.

### 2. The workflow that runs the board was not protected
`ci/run_gates.py`, `ci/checks.yaml`, `ci/regenerate.sh` and `ci/test_hooks.sh` are all in the protected set. `.github/workflows/gates.yml`, which invokes them, was not. An executor could edit or disable CI outright and neither `guard-machinery` nor gate E2 would have said anything — the loudest possible way to make a board stop failing, and the one route still open. Closed.

That it went unnoticed through revisions 8, 10 and 12 — three passes that each rewrote part of the protected set — says something about how these gaps survive: each pass asked "does this list work?" and none asked "is this list complete?"

---

## Tally and next action

**7 of ~31 done.** No track moved.

1. Publish the data tarball; set `OBC_DATA_URL`, `OBC_PDF_URL_V1`, `OBC_PDF_URL_V2`, `ANTHROPIC_API_KEY`. Item 1 for a fifth revision.
2. Read the next CI run. It is the only test of the expression form, and if it is a parse error the change reverts in one commit.
3. Once data exists, confirm the fork-PR case skips the fetch and still fails at DATA1.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
