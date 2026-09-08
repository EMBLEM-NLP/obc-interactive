# Gates — E (item E9 only: distribution of the derived data)

**HANDOFF NOTE.** This file belongs at `gates/GATES-E.md`. `gates/GATES-*.md` is
in the protected set (`harden/checks/check41_machinery.py` `PROTECTED`;
`.claude/hooks/protect-checks.sh`; `.claude/settings.json` deny), so an executor
may not create it. A human must review and move it. Until then it is a
proposal, not a ledger.

Staged **flat** under `proposed/E/`, never `proposed/harden/checks/…`: the
mirrored layout is permitted spelled relatively and refused spelled absolutely,
because `check41_machinery.py._candidates()` expands an absolute path into every
suffix of itself, and `…/proposed/harden/checks/x.py` has the suffix
`harden/checks/x.py`. A permission that depends on spelling is not a
permission. Verified for every file staged here, both spellings:

    $ python3 harden/checks/check41_machinery.py --is-protected \
        proposed/E/GATES-E.md proposed/E/check44_distribution.py \
        proposed/E/check22_docs.py <the same three, absolute>
    (no output — none is protected)

The rules this follows (R13 staging, R14 flat-per-track, PROTOCOL step 4a
PROMOTE) and the check that enforces them (`check42_produces.py`, gate E3) are
**not present in this worktree**, which was branched from `5dc7d41` and is four
commits behind the tree they were written on. They were followed as instructed
by the dispatching agent; they could not be verified here. See AUDIT-rev14.md,
WHAT WAS FOUND 1.

**Scope.** This ledger covers **E9 only** — the README describing a tree the
reader does not have. E1–E8 are untouched and are not declared here; they need
the derived data and this clone has none. Track E stays `ready`.

**What this clone is.** 29 of 29 files in `data-manifest.json` are absent
(`python3 harden/checks/check40_dataintegrity.py` → `MISSING: 29`), so
`ci/regenerate.sh` exits 1 and `ci/run_gates.py` aborts at DATA1 after E1/E2.
PROTOCOL steps 5 (RE-BAG) and 6 (VERIFY, corpus mode) are **unreachable here**
and are recorded as unreachable rather than worked around.

---

## Gates

- [ ] DOC1-D1: the front page tells a reader how to obtain the data it does not
      contain. For every path in `data-manifest.json` that is absent from the
      tree, `README.md` must name `ci/fetch_data.sh`.
  CHECK: `python3 proposed/E/check44_distribution.py --only d1`
  EXPECT: `RESULT: PASS`, exit 0. Reports `absent 29 of 29` and
      `README names ci/fetch_data.sh: yes`. Turns red when the pointer is
      removed from the README — proven by control DOC1-C1, not asserted.
  NOTE: D1 is **vacuous on a hydrated tree**: with 0 absent files there is
      nothing it can fail on, and the check says so in its own output
      (`D1 vacuous (nothing absent)`) rather than printing a bare PASS. R4.

- [ ] DOC1-D2: `ci/fetch_data.sh` carries a location a reader can resolve, not a
      placeholder.
  CHECK: `python3 proposed/E/check44_distribution.py --only d2`
  EXPECT: **`RESULT: FAIL`, exit 1 — today and until a human publishes the
      release.** Every location in the script's header is
      `https://…/obc-interactive-data.tar.gz` or
      `https://…/releases/download/data-v1`: the host is the ellipsis `…`.
      0 of 3 candidate locations resolve.
  THIS IS DELIBERATE. D2 is red because no public release exists. It is not
      softened to a warning, it is not deferred, and D1 passing does not mask
      it: the two halves exit independently (`--only d1` / `--only d2`) and the
      default run fails while either half fails. **Turning D2 green is a human
      act** — publishing the artifact and writing its URL into
      `ci/fetch_data.sh`. No executor may close it by editing the check.

- [ ] DOC1-C1 (control for D1, both directions): D1 measures the README and can
      go both ways.
  CHECK: `python3 proposed/E/check44_distribution.py --controls`
  EXPECT: line `C1 strip-pointer` reads `ok` — untouched README `exit 0`,
      README with every `ci/fetch_data.sh` occurrence removed `exit 1`.
      The mutation targets the mechanism (the README under test) and never the
      ground truth (`data-manifest.json`, which decides what is absent). R2.

- [ ] DOC1-C2 (control for D2, both directions): D2 measures the location and is
      not a constant `FAIL`.
  CHECK: `python3 proposed/E/check44_distribution.py --controls`
  EXPECT: line `C2 restore-placeholder` reads `ok` — a copy of
      `ci/fetch_data.sh` with the `…` replaced by a real host `exit 0`, the
      placeholder restored `exit 1`.
  WHY BOTH DIRECTIONS. A check that always fails passes a mutation-only test,
      and a check that always passes passes a pass-only test. `check41` shipped
      with a one-directional control and CI run 11 found it firing on `mtime`
      for files nothing had changed — a false red, which gets a gate ignored
      just as thoroughly as a false green (`harden/checks/check41_machinery.py`
      lines 145–158 and 214–221). Both of C1 and C2 assert the green direction
      **and** the red direction.

- [ ] DOC1-H10: not applicable — **DOC1 reports no ratio and has no floor.**
      Stated rather than omitted. R1 requires a registered mutation for every
      gate that reports a ratio; DOC1 reports two booleans and two counts.
      `harden/checks/check35_controls.py` has exactly two registry shapes — a
      metric ratio over `obc-mod.sqlite`, and `SUBPROCESS_CONTROLS` whose
      scopes are `harden` (mutates a graph via `OBC_GRAPH`), `retrieval`, and a
      `verify/` working set. Neither shape can express a package-level document
      check, and check35 cannot run on this clone at all
      (`FileNotFoundError: emitters/obc-mod.sqlite does not exist`). Staging a
      registry fragment that could not be exercised here would be decoration,
      which is what R11 forbids. DOC1's controls are therefore carried by the
      shipped check itself, run as a black box in a subprocess, both
      directions. The durable fix — a `pkg` scope in `SUBPROCESS_CONTROLS` so
      DOC1-C1/C2 join H10 — is proposed in the audit addendum, not applied.

---

## Staged, then promoted

`gates/`, `harden/checks/` and `retrieval/checks/` are refused to every
executor. These files are staged flat under `proposed/E/`; a human promotes
them (PROTOCOL step 4a).

| staged | destination | why staged |
|---|---|---|
| `proposed/E/GATES-E.md` | `gates/GATES-E.md` | `gates/GATES-*.md` protected |
| `proposed/E/check44_distribution.py` | `harden/checks/check44_distribution.py` | `harden/checks/*` protected |
| `proposed/E/check22_docs.py` | `harden/checks/check22_docs.py` | `harden/checks/*` protected |

Not staged, because they are not protected and were edited in place:
`README.md` (split), `PACKAGE.md` (new), `harden/gen_readme.py` (output path
only), `ci/fetch_data.sh` (`--where` mode). `ci/fetch_data.sh` is **not** in
`PROTECTED` — `ci/checks.yaml`, `ci/run_gates.py`, `ci/regenerate.sh` and
`ci/test_hooks.sh` are, and `ci/*` is not. Confirmed with
`python3 harden/checks/check41_machinery.py --is-protected ci/fetch_data.sh`
(empty output).

## What H3 measures until check22 is promoted

`harden/checks/check22_docs.py` in force today reads `README.md` and requires
every figure of three digits or more in it to appear in `FACTS.json`. After the
split, the measured figures live in `PACKAGE.md`. **Until a human promotes
`proposed/E/check22_docs.py`, H3 measures a README that no longer carries those
figures.** That is H3 reading green for the wrong reason, and it is named here
rather than left to be discovered:

1. The figures H3 exists to police — 27,421 nodes, 3,928 bookmarks, 35,932
   internal links — are no longer in the file H3 reads. H3 would pass over a
   `PACKAGE.md` it never opens.
2. The two figures the new README *does* carry, `338,348,579` and `29`, come
   from `data-manifest.json`, which is **not** in `FACTS.json`. The in-force H3
   would flag `338,348,579` as `README states figures nothing measured` — a
   **false red**, and the second wrong-reason outcome of the same split.

The staged `check22_docs.py` fixes both: it applies the figure test to
`PACKAGE.md` against `FACTS.json`, applies it to `README.md` against
`data-manifest.json`, and keeps the required-statement test on `README.md`.
Neither behaviour could be executed here — `harden/gen_readme.py` opens
`emitters/obc.sqlite` and the two built PDFs, all 29 of which are absent — so
the staged check is reviewed, not verified, and says so in its own docstring.

## Required statements that constrain the split

`README.md` may not lose these, whatever moves to `PACKAGE.md`:

- H3 (`check22_docs.py`): `Unofficial`, `free of charge`, `King's Printer`,
  `HANDOFF REQUIRED`, `current to`.
- G16d (`verify/emitters/checks/check19_package.py:87`): `Unofficial`,
  `free of charge`, `King's Printer`, `HANDOFF REQUIRED`, `E4`.

`HANDOFF REQUIRED` and `E4` sit in the completion table, which E9 moves to
`PACKAGE.md`. Moving the table wholesale would turn both checks red on their
required-statement assertion. The measured four-row table therefore moves; a
short prose statement of the same handoff — naming `HANDOFF REQUIRED` and `E4`
— stays on the front page, where a reader needs it anyway. Verified with
`python3 proposed/E/check44_distribution.py --statements`.

## Run log, 2026-09-08

Boxes stay unticked. A gate is ticked from a clean bag in PROTOCOL step 6, and
step 6 is unreachable here (DATA1, 29 of 29 files absent). These are the runs.

| command | exit | result |
|---|---|---|
| `python3 proposed/E/check44_distribution.py --only d1` | 0 | `D1 PASS` — 29 of 29 absent; README names `ci/fetch_data.sh` (6 occurrences) and all 3 source modes |
| `python3 proposed/E/check44_distribution.py --only d2` | 1 | `D2 FAIL` — 0 of 4 locations resolve; 3 ellipsis placeholders, 1 `<host>` placeholder |
| `python3 proposed/E/check44_distribution.py` | 1 | `DOC1 halves: D1 PASS, D2 FAIL` — the halves do not mask each other |
| `python3 proposed/E/check44_distribution.py --controls` | 0 | `C1 strip-pointer ok` (untouched 0, mutated 1); `C2 restore-placeholder ok` (repaired 0, placeholder 1) |
| `python3 proposed/E/check44_distribution.py --statements` | 0 | 6 of 6 required statements present in `README.md` |
| `OBC_README=<copy with the pointer stripped> … --only d1` | 1 | D1 red on a temp copy; the real `README.md` was never edited |
| `OBC_FETCH=<copy with a real URL> … --only d2` | 0 | D2 green on a temp copy — 1 of 4 resolves. D2's red is a measurement, not `sys.exit(1)` |
| `bash ci/test_hooks.sh` | 0 | E1 `RESULT: PASS`, 77 cases |
| `python3 harden/checks/check41_machinery.py` | 0 | E2 `RESULT: PASS` — 95 protected files, **0 modified, 0 untracked** |
| `bash ci/regenerate.sh` | 1 | step 5 unreachable: *"Refusing to regenerate - a manifest built now would describe a tree that does not exist."* |
| `python3 ci/run_gates.py` | 1 | step 6 unreachable: E1 PASS, E2 PASS, DATA1 FAIL `MISSING: 29`, board aborts |
| `python3 harden/checks/check35_controls.py --db emitters/obc-mod.sqlite` | — | did not run: `FileNotFoundError: emitters/obc-mod.sqlite does not exist`. No H10 entry is owed; see DOC1-H10 above |

`harden/gen_readme.py` is **unexercised**. It opens `emitters/obc.sqlite` and
both built PDFs, none of which is in a git checkout. The change to it is two
executable lines, both the output path (`git diff -U1 harden/gen_readme.py`);
nothing here establishes that it runs.

---
Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the
official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
