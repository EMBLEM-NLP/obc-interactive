---
name: rebuild-validate-bag
description: Regenerate derived artifacts in dependency order, rebuild the BagIt bag with the project's own tooling, and validate it with the user's unmodified checks. Use at step 5 (RE-BAG) of every track and before any commit.
allowed-tools: Bash, Read
disable-model-invocation: true
---
# Rebuild and validate the bag

Run `scripts/rebag.sh`. It does, in this order and no other:

1. `bash ci/regenerate.sh` — README + FACTS.json (gen_readme.py) → MANIFEST.sha256 → RO-Crate + in-toto (make_provenance.py). Each depends on the one before; H3 and G16d both went red when this was done by hand out of order.
2. `touch .regen.stamp` — the `guard-commit` hook refuses `git commit` unless this is newer than every tracked file.
3. Rebuild the bag with `harden/make_bag.py` logic (bagit library; the two source-PDF hashes carried from `ci/checks.yaml` `sources`, not recomputed — the PDFs are fetch-only).
4. `check21_bagit.py` (H2) and `check26_provenance.py` (H8), **unmodified**, via `OBC_BAG` / `OBC_PKG`.

Both must print `RESULT: PASS`. The bag is "incomplete as expected" — two fetch.txt payloads absent — and that is correct.

This skill is user-invocable only (`disable-model-invocation`): it writes the manifest that everything else is verified against.
