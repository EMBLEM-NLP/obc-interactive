# Orchestration protocol

Every track executor — a person, a CI job, a subagent — follows this. It is not process for its own sake; each rule below is here because its absence produced a defect that shipped green. Six vacuous gates, four masked fixes, and one audit that said "no RO-Crate" over a tree root it never listed.

---

## The cycle

Every track runs the same seven steps. None is optional. A track that skips one is not done; it is a pack awaiting integration.

```
1. DECLARE    gates in gates/GATES-<track>.md BEFORE writing code
2. BUILD      in a copy of the package tree, never in the bag
3. MUTATE     register an H10 control for every ratio gate; run check35
4. INTEGRATE  place files at real, convention-matched paths; wire orchestration
5. RE-BAG     rebuild with harden/make_bag.py logic; regenerate provenance
6. VERIFY     with the user's own unmodified checks: check21, check26, and
              every gate the track touched, in corpus mode, from a CLEAN bag
7. AUDIT      append to AUDIT-rev<N>.md: what moved, what did not, what broke
```

**What "done" means:** step 7 is written and every gate in step 1 passes in step 6. Not step 2. Not step 4. Revision 1 of the audit found seven items "built and verified" and zero integrated; that gap is the reason this document exists.

---

## Rules, each with the defect that wrote it

### R1 — A ratio gate without a registered mutation is void, however green.
Every check that reports a ratio registers a mutation in `harden/checks/check35_controls.py` that drives it below its floor. The mutation runs the *shipped script* as a black box, twice: untouched must exit 0, mutated must exit non-zero.
*Wrote it:* `check33` scored a set against itself (100.0000% identically). `check4` and `check24` MR1 compared corpus-wide multisets with a 71% surplus — blanking all 7,667 sentences registered as 0.14%. `check31` gated on a hand-written label, not the overlap it measured.

### R2 — Mutate the mechanism, never the ground truth.
A mutation must target the pipeline output the check scores, not the source the check scores it against. Deleting the `ref` table shrinks both sides of a resolution ratio and leaves it at 100%.
*Wrote it:* my own first C1 control, same tautology as `check33` one level up.

### R3 — Corpus mode gates. Eval mode is convenience.
Every completeness or delivery metric runs `--all-articles` before a track closes. Twenty-six eval targets passed; the corpus run found two hub articles at 1/677 and 7/382.
*Wrote it:* the 90.06% delivery finding that 50 questions could not surface.

### R4 — Any aggregate over a structure with surplus is vacuous.
If the "captured" side of a comparison is larger than the "source" side, nothing removed from the source can register. Compare per unit — per page, per node — so the surplus is out of the denominator.
*Wrote it:* three checks, one root cause.

### R5 — A digest that excludes something is blind to exactly that thing.
`check20` excluded `meta` from its determinism digest. The only nondeterminism in the build was in `meta`. Hash the whole artifact, or enumerate the exclusion as a known gap in the gate text.

### R6 — A read-time workaround is not a fix. Label it MASKED.
Suppressing flattened table text in the renderer left 303,204 characters in the stored vectors. Following `node.parent` as a fallback left the emitter writing one fact two ways. Both looked fixed. Neither was. The audit status for these is `MASKED, not fixed`, and it stays there until the source changes.

### R7 — Every path resolves from the package root with an env override.
No `/home/claude/...`, no `/mnt/...`. Fetch-only inputs (the source PDFs) use `OBC_SRC_V1` / `OBC_SRC_V2` and fail with a stated reason, never a traceback.
*Wrote it:* H1, H4, H5 were green and could not be re-run by anyone who received the bag. `emit_common.py` hardcoded its input; the shipped `obc.sqlite` could not be regenerated.

### R8 — One re-embed per batch.
Fixes that invalidate vectors land together, then embed once. B1, B2, B3 together is one embed; separately is three for identical output.

### R9 — Documentation is measured, not typed.
Every number in a report is produced by a check and cited to it. `check22_docs.py` enforces this for `README.md`; Track E7 extends it to `reports/*.md`, where two files still describe closed phases as future work.

### R10 — Audit yourself at the same standard.
Correction is recorded, not overwritten. Revision 1 of the audit was wrong about RO-Crate; it is preserved unedited with the correction beneath it. "One line each" was wrong by a factor of three; revision 3 says so in its first section. An audit that retouches its own past findings is a status report.

---

## Handoff contract

Tracks communicate through the bag, not through chat.

**A track receives:** the current `obc-interactive-bag-integrated.zip`, its work package in `orchestration/work-packages/`, and `tracks.yaml`.

**A track returns:**
1. A rebuilt bag that passes `check21_bagit.py` and `check26_provenance.py` unmodified.
2. Its gate file, every gate `[x]` with `automatic-evidence=v1` digests, every ratio gate listed in `check35`'s registry.
3. An audit addendum: what moved, what did not, what broke, what was found. The "found" section is mandatory — every track so far has found something the previous one missed.
4. `tracks.yaml` updated: its own status, and any new item it discovered added under the correct track.

**A track may not return:**
- A pack of loose files (that is step 2, not step 7).
- A gate marked `[x]` without a corpus-mode run.
- A status of `done` for anything the source data does not reflect.

---

## Parallelism

`schedule.py` reads `tracks.yaml` and reports what is `ready`. Tracks listed under `parallel_with` may run concurrently on separate copies of the package tree; they merge by rebuilding the bag in dependency order. Two tracks editing the same file — `check35_controls.py`, `obc_agent_tools.py` — serialise on that file.

The critical path is A2 → A4 → B → G → FSCOPE → D. Everything else is parallel to it. Do not let C, E, or MAINT starve the critical path of attention; they are important and they are not blocking.

---

## What the executor cannot do here

This protocol was written in an environment with no subagent dispatch, no CI runner, and no source PDFs. Three consequences, stated so the next executor does not discover them the hard way:

- The GitHub Actions workflow in `ci/` is syntactically valid and has never been executed. It is not "live" until a hosted run is green.
- `check0`, `check8`, `check15`, `check28` need the fetch-only PDFs. They are excluded from the local board with a stated reason and must be run by whoever holds the PDFs.
- Decisions DEC1–DEC4 in `tracks.yaml` require a human. No track may resolve them by assumption.

---

Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). Not the official Building Code Compendium.
© King's Printer for Ontario, 2024. Reproduced with permission.
