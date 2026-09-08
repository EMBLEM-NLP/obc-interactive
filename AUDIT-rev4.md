# Track audit — revision 4

After the orchestration pass. Revisions 1–3 preserved unedited.

**Headline: A2 is done — every gate runs from the bag on a single command, the board is machine-readable, and the runner carries its own controls. An orchestration layer now exists that subagents could execute against. No subagents were provisioned, because none can be from here, and saying so is the first line of the protocol.**

---

## What "provision subagents" meant in this environment

There is no agent-dispatch tool in this session. What was asked for cannot be done here literally, and pretending otherwise would be a green board over nothing.

What was built instead is the layer without which parallel executors — subagents, people, CI jobs — would produce more of exactly what this project has spent the week finding: gates that pass and cannot fail, fixes that mask, docs that drift. Specifically:

| artifact | what it is | verified how |
|---|---|---|
| `orchestration/tracks.yaml` | the dependency DAG, single source of truth for 14 tracks, 4 pending decisions | `schedule.py --check` PASS; negative control: a status contradicting the graph is rejected with exit 1 |
| `orchestration/PROTOCOL.md` | the seven-step cycle and ten rules, each tied to the defect that wrote it | — |
| `orchestration/schedule.py` | derives ready / blocked / critical path; never trusts a typed status | 4 ready, 5 blocked with reasons, 1 conditional; ~17 weeks with FRULES, ~9 without |
| `orchestration/work-packages/*.md` | 14 self-contained briefs, generated from the DAG so they cannot drift from it | regenerated after a YAML fix; verified intact |
| `ci/run_gates.py` + `ci/checks.yaml` | executes every check in its correct context; SKIPs fetch-only inputs with a stated reason | 38 gates, 30 pass, 0 fail, 1 known-review, 7 skip |
| `ci/regenerate.sh` | derived artifacts in dependency order: docs → self-manifest → provenance | H3 and G16d both went red when this was done by hand out of order |
| `.github/workflows/gates.yml` | the trigger | **never executed** — stated in the file's own header |

---

## What A2 found on its first run

Eight failures, each classified rather than suppressed:

- **G7 `check6_figures` — a real gap surfacing through CI for the first time.** The 313 exported figure image files were never packaged (Track E6, already enumerated). The check is green in the build session and REVIEW from the bag: the same "green but unreproducible" class as H1/H4/H5 were yesterday. Marked `KNOWN` on the board with the reason; it does not fail the run and it is not hidden.
- **H3 `check22_docs` — the drift gate doing its job on me.** Striking R4, G5, V3 and adding `GATES-remediation.md` changed the ledger facts; README and FACTS.json still described the old state. Regenerated. Then G16d caught that `MANIFEST.sha256` was now stale relative to the regenerated README — hence `regenerate.sh`, so the order cannot be gotten wrong by hand again.
- **H2, G16d — runner bugs.** The CI bag builder did not inject the fetch-only source hashes; the package check needed the deliverable zip built first. Fixed; sources are data in `checks.yaml`, not code.
- **H7 `check27` — a portability miss.** Yesterday's pass rewrote the nine BLOCKED files. Five others had env vars whose *defaults* still pointed at the build session; they ran only when the env was set explicitly. All five fixed, plus two more in `test_properties.py` and `control_negative.py`. **All 60 check files: zero bare build-session paths.** Fifteen remain in pipeline *stages* and the two packaging tools — defaults for source PDFs that orchestrators pass explicitly — enumerated as PORT residual.
- **R1, R3, R5 — environment, not defect.** The three embedding checks need `sentence-transformers`. Now SKIP with the reason *"CI must pip install it"* rather than fail. The workflow installs it.

And one bug in my own patch that did nothing: a regex that assumed one space where the YAML had two. `needs_module` was applied to zero entries and I only knew because the board said so. Rule R1 applies to patches too.

---

## The runner's own controls

**CI1 — can the board go red?** Seed a check whose only output is `RESULT: FAIL`, run the board, require exit 1. It does. A runner that cannot go red is a light, not a gate.

**CI2 — is the board reproducible?** Two full runs from clean state, compared on every (gate, status) pair: 38 of 38 identical. `generated` is derived from `SOURCE_DATE_EPOCH`, not the clock.

---

## Track status

| track | status | change this pass |
|---|---|---|
| A1 integrate | **DONE** | — |
| A2 CI | **DONE, trigger unverified** | runner verified locally; hosted run never happened |
| A3 mutation controls | **DONE** | — |
| PORT portability | **DONE** | five more defaults fixed; checks at zero; stages enumerated |
| A4 schema | **READY** | unblocked, not started |
| B | blocked on A4 | — |
| G | blocked on B | surface DONE; G1–G4 not started |
| FSCOPE, D, FOBJ | blocked | — |
| C, E, MAINT | **READY** | not started |
| FRULES | conditional on DEC1 | — |

**Honest tally: 5 of ~30 done** (A1, A2, A3, PORT, G surface). Revision 3 said four.

**Ready now, in parallel:** A4 (critical path), C, E, MAINT. The scheduler says so; it is derived, not typed.

---

## Board, as shipped in `ci/gate-board.json`

```
ran 29 | passed 30 | failed 0 | known-review 1 | skipped 7

known-review  G7        figure assets never packaged (E6)
skipped       G1 G8 V8 H9   fetch-only source PDFs unset
              R1 R3 R5     sentence-transformers not installed here
```

Thirty gates pass from a clean bag with one command. Seven cannot run here and say why. One is a known gap and says which track owns it. Zero are silent.

---

## Decisions still pending

Four, unchanged, and now enumerated in `tracks.yaml` where `schedule.py` prints them on every run: assist-or-judge (DEC1, blocks FRULES and G4's refusal set), external exposure (DEC2), the hub token cap (DEC3), and two days of a building official (DEC4, blocks D3, D4, and FSCOPE's S3). No executor may resolve these by assumption; the protocol says so.

## Next

Four tracks are ready and independent. The critical-path one is **A4 — the declared schema.** Its work package is written. Its first exit criterion is that the three dual-encoding defects this project has already shipped become unrepresentable.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
