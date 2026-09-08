# 2024 Building Code Compendium — interactive edition and document model

**You are reading the source checkout.** This repository is the code, the
checks and the orchestration. It does **not** contain the 29 derived
binary artifacts the project produces — 338,348,579 bytes of PDFs,
databases and archives — and a fresh clone never will. `PACKAGE.md` describes
the *hydrated package*, and every count in that file is measured from those
artifacts at package time. None of them is true of a clone until you fetch the
data.

Saying which tree a document describes is the whole point of this split. The
previous single README opened by asserting that its numbers were "measured from
the artifacts at package time" and then described a `pdf/` directory the reader
did not have, with nothing anywhere telling them where to get it.

**Unofficial.** Current to **16 January 2025** (through **O. Reg. 5/25**).
Not the official Compendium. Consult the official edition published by
Publications Ontario for authoritative text.

---

## What a clone contains

| | |
|---|---|
| `pipeline/` | the deterministic build — stages 0–9, Volume 2, the merge, the emitters |
| `retrieval/` | definitions, embeddings, fusion, the agent tool surface |
| `harden/` | packaging (`make_bag.py`, `make_provenance.py`), the docs generator, and `harden/checks/` |
| `verify/`, `pipeline/*/checks/` | the per-phase checks, each with its own working set |
| `gates/` | the acceptance ledgers — one gate per claim, each with the command that decides it |
| `ci/` | `run_gates.py`, `checks.yaml`, `regenerate.sh`, `fetch_data.sh`, `test_hooks.sh` |
| `orchestration/` | `tracks.yaml` (the DAG), `PROTOCOL.md` (seven steps, ten rules), work packages |
| `schema/`, `model/`, `reports/` | the declared schema, the graph's shape, the phase-by-phase record |
| `data-manifest.json` | every derived binary the gates read, with size and sha256 |
| `.claude/` | hooks, skills, agent specs and the MCP server that make the rules refuse rather than advise |

Nothing here is generated at clone time. `pipeline/run.sh` rebuilds the derived
artifacts from the two source PDFs; `ci/fetch_data.sh` downloads them instead.

## What a clone deliberately excludes

`data-manifest.json` lists **29 files, 338,348,579 bytes**, none of
which is in git:

| directory | files | what |
|---|---|---|
| `pdf/` | 4 | the interactive Volume 1 and Volume 2, protected and unencrypted |
| `emitters/` | 5 | `obc.sqlite`, `obc-mod.sqlite`, `obc-vec.sqlite`, the Markdown and HTML archives |
| `model/` | 5 | the canonical document graph and the intermediate models |
| `verify/data/` | 15 | the frozen per-phase working sets the checks read |

Three reasons, in the order they bind:

1. **Crown copyright.** The two source PDFs (Publications Ontario #301880 and
   #301881) are fetch-only and are never redistributed here — see
   `ci/fetch_sources.sh` and the `fetch.txt` of the bag. The derived artifacts
   are permitted for non-commercial redistribution only while they are free to
   the public; see *Licence and attribution* below before you mirror them.
2. **Size.** The repository is a few hundred kilobytes of code. The data is
   three orders of magnitude larger, changes as a block, and is regenerable.
3. **The Git-LFS-pointer hazard.** LFS is deliberately not used.
   `harden/checks/check40_dataintegrity.py` documents why: Claude Code's cloud
   sandbox proxy rejects the LFS batch endpoint, so an LFS-tracked database
   clones as a ~130-byte text file beginning
   `version https://git-lfs.github.com/spec/v1`. That file opens without error.
   `sqlite3.connect` succeeds on it; the first query fails, or worse, a checker
   that counts rows reports zero and a ratio computed over zero denominators
   reports 100%. A silently empty database is a worse outcome than an absent
   one, so the data is absent, and `check40` fails closed on both.

The absence is not a surprise to the machinery. `.gitignore` lists the patterns,
`data-manifest.json` records every file with its sha256, and gate **DATA1**
(`python3 harden/checks/check40_dataintegrity.py`) fails red naming each missing
file on every run, before any gate that would read them:

```
$ python3 ci/run_gates.py
DATA1  FAIL  ...  MISSING: 29
```

That is correct behaviour, not a broken checkout.

## How to hydrate a clone

```bash
bash ci/fetch_data.sh --where     # what to set, and what it must point at
bash ci/fetch_data.sh             # fetch, verify against data-manifest.json, install
```

`ci/fetch_data.sh` takes exactly one of three sources:

| variable | value | when |
|---|---|---|
| `OBC_DATA_TARBALL` | a URL or local path to `obc-interactive-data.tar.gz` | the normal case; matches the artifact this project ships |
| `OBC_DATA_DIR` | a path to a full tree that already holds the files | another checkout, a mounted volume, a CI cache |
| `OBC_DATA_URL` | a base URL serving one asset per file, `/` replaced by `__` | a GitHub release, whose asset names cannot contain slashes |

Every file is verified against its sha256 in `data-manifest.json` *before*
anything is installed, so a truncated download or a corrupted archive aborts and
leaves the tree untouched. Re-running is cheap: files already correct are
skipped. The script finishes by running `check40` in `--quick` mode.

**There is no public release yet, and no URL you can paste.** The location
placeholders in `ci/fetch_data.sh` are literally `https://…/` — an ellipsis
where the host belongs. Publishing the artifact is a human act that has not
happened. Until it does:

- `OBC_DATA_DIR` is the only mode that works without one, and it needs someone
  to hand you a hydrated tree;
- gate **DOC1-D2** (`harden/checks/check44_distribution.py --only d2`) is
  **red on purpose** and stays red until a real URL is written into
  `ci/fetch_data.sh`. It is not a warning and it is not deferred. A green board
  is not available to this project while its own data cannot be obtained.

Without the data you can still run: `bash ci/test_hooks.sh` (E1),
`python3 harden/checks/check41_machinery.py` (E2),
`python3 orchestration/schedule.py`, and every check marked `no_data:` in
`ci/checks.yaml`. Everything else is skipped with its reason recorded, never
counted as a pass.

## Completion status

**HANDOFF REQUIRED.** Four gates in this project are abandoned rather than met:
**E4** (manual WCAG review — no screen reader, contrast analyser or human
reviewer was available), and **G5**, **V3** and **R4**, superseded because the
checks behind them could not fail. Each carries an `ABANDON:` line in its ledger
stating why. The package is not "complete" without that qualification, and
WCAG 2.2 AA conformance **cannot be claimed** from the mechanical structure
checks alone.

The measured ledger table — which ledger, how many met, how many abandoned — is
in `PACKAGE.md`, beside the artifact counts it belongs with. `FACTS.json` holds
the same numbers as data. `gates/` holds the ledgers themselves.

## Working in this repository

`orchestration/tracks.yaml` is the DAG and `python3 orchestration/schedule.py`
says what is ready. Every track follows the seven steps in
`orchestration/PROTOCOL.md`. Verification machinery — `harden/checks/`,
`*/checks/`, `ci/`, `gates/`, `.github/workflows/`, `.claude/hooks/` — is
read-only to an executor; `harden/checks/check41_machinery.py --list` prints the
protected set and gate **E2** detects drift in it however it was produced.

Four decisions require a human and may not be resolved by assumption: DEC1
assist-vs-judge, DEC2 external exposure, DEC3 hub token cap, DEC4 building
official.

## Licence and attribution

© King's Printer for Ontario, 2024. Reproduced with permission.
Contains material copyrighted by the National Research Council of Canada,
reproduced under a licence agreement.

**Permitted for personal use and non-commercial reproduction and distribution
only, and only where this product is made available to the public free of
charge.** Any use that is not free to the public is treated by the Ministry of
Municipal Affairs and Housing as commercial use and requires a licence:
`buildingtransformation@ontario.ca`

Material must be reproduced accurately and must not be presented as an official
version of the Government of Ontario.

Official sources:
- Volume 1 — https://www.publications.gov.on.ca/store/20170501121/Free_Download_Files/301880.pdf
- Volume 2 — https://www.publications.gov.on.ca/store/20170501121/Free_Download_Files/301881.pdf
