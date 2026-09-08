# Gates: Volume 2 ingestion

OWNS: checks/**, out/**, GATES.md

Scope: the 2024 Building Code Compendium Volume 2 (301881.pdf, 1,001 pages)
is parsed to the same standard as Volume 1 and merged into the document graph
so the 1,054 references that currently resolve to nothing are closed.

- [x] V1: every glyph Volume 2 renders is captured in the page inventory
  CHECK: python3 checks/check0_coverage.py out/inventory.jsonl.gz "$OBC_SRC_V2"
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=7cb94d52b430dd53da2dbdd0ffb26e463be079e904400a0075b9fbb31fc8bd7b; exit=0; EXPECT=matched; output-sha256=11ce7d8756265d816f744cdbf96040907d8853346023ffc946f6edf6ab79f8c8; output-bytes=366; shell=/bin/sh; cwd=/home/claude/verify/volume2; path=2d5a7faa1724/9 entries

- [x] V2: every table and figure Volume 2 declares is detected as a region
  CHECK: python3 checks/check1_regions.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=105df8249507a949893deed157dd1e29c0d4a56629557230a4f398e859f72db0; exit=0; EXPECT=matched; output-sha256=f99be734de720da53e5c0347da06d66dd3631c5248f64a52a38f4578b3db91d7; output-bytes=325; shell=/bin/sh; cwd=/home/claude/obc2; path=2d5a7faa1724/9 entries

- [ ] V3: Volume 2's structure is assembled into a node tree with no text dropped

ABANDON: V3 SUPERSEDED 2026-09-07. The check behind this gate, check4_capture.py, could not fail: it compared corpus-wide character multisets with a 71% surplus, and blanking 100% of sentence text left orphaned at 0.140% < 0.5%. The evidence digest for that run is real — the check ran and exited 0 — and proves nothing about capture. Replaced by check4b_capture.py (per-page), controlled in check35. No CHECK can decide a superseded outcome, so this gate carries none. The line removed with this edit read `CHECK: python3 checks/check4b_capture.py`, and its evidence digest (definition-sha256=fb69210e9f94…, exit=0, EXPECT=matched) is preserved here rather than deleted: the pass proves nothing about the claim, and the record of a vacuous pass is the part worth keeping.

- [x] V4: containers, Appendix A notes and Supplementary Standards are addressable
  CHECK: python3 checks/check12_vol2.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=00b7030ac13b888d12782f49bc74b9866b7c801165e1cc5e8b2eb727b3be0936; exit=0; EXPECT=matched; output-sha256=91f06b6a6737f52ad8cfb2fe7361250ba88537caa4f3ffd3a750602b2197f7f7; output-bytes=284; shell=/bin/sh; cwd=/home/claude/obc2; path=2d5a7faa1724/9 entries

- [x] V5: the Volume 1 and Volume 2 graphs merge into one addressable model
  CHECK: python3 checks/check13_merge.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=3b485e5261c9987353bab7d743cda5c7d4068ca49262076b5b7d6adbdc92e86e; exit=0; EXPECT=matched; output-sha256=95772097ec3ad3a017e2d44bc1a0e7c399953b3633ba11229ac6fd0faa1d5b61; output-bytes=236; shell=/bin/sh; cwd=/home/claude/obc2; path=2d5a7faa1724/9 entries

- [x] V6: Volume 1's references into Volume 2 resolve after the merge
  CHECK: python3 checks/check14_crossvol.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=4fd1be1bcb2e95d36b029da878332e558643466fe906ebe3a2ba2eabfbea79ea; exit=0; EXPECT=matched; output-sha256=40c5f864313675c4edfe295a9238532036c2203a91a0ce06ec5f2ebc10958a82; output-bytes=308; shell=/bin/sh; cwd=/home/claude/obc2; path=2d5a7faa1724/9 entries

- [x] V7: Volume 2 is rebuilt as an interactive PDF from the merged model
  CHECK: python3 checks/check15_vol2build.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=39fc14fe6d784194cb3baffe9f653c8f2ab1d7ace5ada295935b86b978a44874; exit=0; EXPECT=matched; output-sha256=d0416c37467ae439e665b2a2ccf927ae563d7ec6680dbfe4706574742f829854; output-bytes=345; shell=/bin/sh; cwd=/home/claude/obc2; path=2d5a7faa1724/9 entries
