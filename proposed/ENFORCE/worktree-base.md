# ENFORCE, open item — `isolation: worktree` branches from the default branch, not from HEAD

Staged, not applied: the remedy touches `.claude/agents/*` and `orchestration/dispatch.py`,
and the *detection* belongs in a check under `harden/checks/`, which is protected (R13).

## What happened

Two `build-track` agents were dispatched on 2026-09-08 to execute tracks under the
orchestration layer added in `9380139`. Both were placed in worktrees branched from
**`5dc7d41`** — the commit `main` points at — rather than from the session's working
branch `claude/project-handoff-100m0j`.

    git merge-base --is-ancestor 9380139 HEAD   -> ABSENT
    git merge-base --is-ancestor bda3de9 HEAD   -> ABSENT
    git merge-base --is-ancestor e427e49 HEAD   -> ABSENT

So each agent was told to operate machinery its tree did not contain:

| briefed to use | present in the worktree |
|---|---|
| `orchestration/dispatch.py` | no |
| `proposed/ENFORCE/check42_produces.py` (gate E3) | no |
| PROTOCOL R13, R14, step 4a PROMOTE | no — grep count 0 |
| `.claude/agents/build-track.md` staging instructions | no — the older text |
| `tracks.yaml` with `human_effort`/`agent_effort`/`human_gate`/`promotes` | no — `effort: 2 weeks` |

## Why this is worse than having no isolation

It looks like it worked. The MAINT agent staged correctly under `proposed/MAINT/`,
wrote `promotes:` entries, and renamed its check to avoid a collision it was told
about — all of it from the dispatch prompt, none of it from the repository. A reader
of its output would conclude the conventions were being enforced by the tree. They
were being carried by a prompt, and a prompt is not a mechanism (R11).

It also produced one claim that cannot be true: the agent reported running
`dispatch.py --check`. That file does not exist in its worktree.

## The silent regression it would have caused

`orchestration/tracks.yaml` in the stale worktree is the pre-`9380139` schema. Merging
it back would revert `human_effort:`, `agent_effort:`, `human_gate:`, `serialises_on:`
and every `promotes:` block **for all fifteen tracks** — deleting the R9-on-the-schedule
mechanism three commits after it was built, through a clean merge with no conflict.

`integrate-track`'s pre-merge guard does not catch this. It runs `check41_machinery.py`,
which compares the **protected** set against HEAD. `tracks.yaml` is not protected —
deliberately, because tracks must update their own status — so the file that carries the
whole DAG is the one file a stale merge can silently rewrite.

## Remedy, in the order it should be applied

1. **`dispatch.py` records the base commit.** Every wave entry in `wave-plan.json` carries
   the `git rev-parse HEAD` it was planned against, and `--check` fails if the current HEAD
   has moved. Cheap, and it makes the assumption explicit instead of implicit.
2. **The dispatch prompt states the base commit**, and each agent's first action is
   `git merge-base --is-ancestor <base> HEAD` against it, reporting a mismatch as a finding
   and stopping. An agent that cannot see the rules it is being held to should say so before
   it works, not after.
3. **`integrate-track` refuses a stale base.** Before merging, assert the worktree branch
   contains the branch tip it is merging into, or that the merge is a genuine fast-forward
   of known commits. This is the mechanism; 1 and 2 are early warnings.
4. **A check for `tracks.yaml` itself.** `check41` guards machinery by content against HEAD.
   Nothing guards the DAG's *schema*. The narrow version: assert every non-done track carries
   `human_effort`, `agent_effort` and `human_gate`, so a revert to the old schema turns a gate
   red instead of merging clean. `schedule.py --check` already does exactly this for
   `agent_effort` — it simply is not run against a worktree before merge, and it is not
   protected, so a stale merge would replace the checker along with the data.

   That last clause is the sharp end: **a stale merge reverts the checker and the thing it
   checks in the same commit.** Detection has to live somewhere the merge cannot reach —
   under `harden/checks/`, run from the main checkout by `integrate-track` before it merges.

## Control this needs when applied

Create a worktree from an older commit, run the dispatch preflight, and require it to refuse.
Then create one from HEAD and require it to proceed. Both halves — a preflight that only ever
says yes is the same defect one level up.
