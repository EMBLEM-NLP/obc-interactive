# Utilization playbook

This file records how Emblem uses this repository in practice.

Active work branch: `claude/project-handoff-100m0j`
Stable promotion target: `main`
Current active tip when this playbook was written: `3b9a1c2cbfb7b1a833237b30ff67fc565d0c72ab`
Date recorded: 2026-09-10

## Role

`obc-interactive` is Emblem's private working repository for the 2024 Ontario Building Code Compendium interactive edition, document graph, retrieval layer, orchestration board, and audit evidence.

Use it for:

- internal OBC study and lookup drills;
- source-grounded pre-review of building-code questions;
- controlled generation of interactive document artifacts;
- evidence-backed audit, gate, and remediation workflows;
- packaging and distribution checks for hydrated artifacts.

Do not use it as:

- an official Building Code Compendium;
- a substitute for Publications Ontario source material;
- a permit authority;
- a licensed architect, BCIN designer, P.Eng., building official, or legal opinion;
- a commercial redistribution package unless the required licensing question has been resolved.

## Branch policy

| branch | role |
|---|---|
| `main` | Stable baseline. Keep it readable, conservative, and demo-safe. Promote to it only after the handoff branch is verified. |
| `claude/project-handoff-100m0j` | Active work branch. Treat this branch as the current source of truth for orchestration, gates, packaging, and audit state. |
| `proposed/<TRACK>/...` paths | Staging locations for verification machinery. Track executors stage here; a human promotes to protected paths. |

The handoff branch is ahead of `main` and carries the live remediation work. Work from it, verify it, then promote intentionally.

## Hydration model

A fresh clone is intentionally data-less. That is correct behavior.

The clone contains code, ledgers, orchestration, checks, manifests, and docs. It does not contain the 29 derived binary artifacts listed in `data-manifest.json`.

Use:

```bash
bash ci/fetch_data.sh --where
bash ci/fetch_data.sh
```

Until a real data release URL exists, the practical path is `OBC_DATA_DIR` pointing at a complete hydrated tree. `DATA1` and `DOC1-D2` remain red until the project can fetch and verify the data it claims to distribute.

## Local operating loop

Start every working session on the active branch:

```bash
git fetch --all --prune
git switch claude/project-handoff-100m0j
git status --short --branch
```

Run the data-independent checks first:

```bash
bash ci/test_hooks.sh
python3 harden/checks/check41_machinery.py
python3 orchestration/schedule.py
python3 ci/run_gates.py
```

If hydrated data is available, fetch or mount it and run the full board:

```bash
bash ci/fetch_data.sh
python3 ci/run_gates.py
```

Before committing generated state:

```bash
bash ci/regenerate.sh
touch .regen.stamp
git add -A
git commit
```

## Human decisions

The repository currently names four decisions that cannot be resolved by assumption:

| id | decision |
|---|---|
| `DEC1` | assist-vs-judge boundary |
| `DEC2` | external exposure |
| `DEC3` | hub token cap |
| `DEC4` | building official |

Do not edit these away. Ask for a human answer, record it, and let the DAG move from the recorded decision.

## Current operating backlog

From `AUDIT-rev16.md`, the next useful actions are:

1. Promote the ENFORCE five first: E3, DAG1, the `ci/checks.yaml` rows, the `guard-commit` worktree patch, and the `guard-machinery` bypass fix.
2. Publish the data release and write the real URL into `ci/fetch_data.sh`.
3. Answer `DEC1` and `DEC2` so the dispatchable wave can move.
4. Decide how to handle gate and track id namespaces before renumbering anything.
5. Keep `GID1` and `GID2` red until the id-space decision is explicit.

## Emblem use cases

### 1. Study drill engine

Use the graph and retrieval layer to build OBC lookup drills that force:

- provision lookup;
- defined-term review;
- article/sentence/clause citation;
- limits of applicability;
- uncertainty notes where the graph says it cannot answer.

### 2. Venue pre-review

Use the repo for internal, non-authoritative pre-review of venue questions such as occupant load, exit assumptions, assembly-use constraints, fire/life-safety prompts, and documentation checklists.

Every output must say when professional review is required.

### 3. Audit control plane

Use `orchestration/tracks.yaml`, `orchestration/board.html`, `gates/`, `reports/`, and `AUDIT-rev*.md` to show what moved, what did not, what broke, and what was found.

The board is generated. Do not hand-type status pages.

### 4. Package and distribution readiness

Use `PACKAGE.md`, `data-manifest.json`, `MANIFEST.sha256`, `ro-crate-metadata.json`, and `attestation.intoto.jsonl` to decide whether a hydrated artifact is reproducible, attributed, and distributable.

No public or client-facing artifact should claim WCAG conformance, official status, or commercial redistribution rights unless the corresponding gate and human review are complete.

## Promotion criteria

Promote from `claude/project-handoff-100m0j` toward `main` only when:

- the branch compare is understood file by file;
- protected verification machinery was promoted by a human;
- data-independent checks pass;
- hydrated checks either pass or fail with explicit known reasons;
- the audit revision records what changed;
- abandoned gates remain labelled as abandoned, not complete;
- README and PACKAGE describe the correct tree;
- copyright and attribution language is preserved.

## Links

- Repository: https://github.com/EMBLEM-NLP/obc-interactive
- Active branch: https://github.com/EMBLEM-NLP/obc-interactive/tree/claude/project-handoff-100m0j
- Stable branch: https://github.com/EMBLEM-NLP/obc-interactive/tree/main
- Compare: https://github.com/EMBLEM-NLP/obc-interactive/compare/main...claude/project-handoff-100m0j

Unofficial derived work. Current to 2025-01-16 through O. Reg. 5/25. Not the official Building Code Compendium.
