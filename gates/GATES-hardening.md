# Gates: hardening (research-directed)

OWNS: checks/**, lib/**, out/**, GATES.md

Scope: replace the ad-hoc fixes with the recognised practice the design review
identified — deterministic builds, BagIt packaging, generated docs enforced by
CI, and a named discipline for making the checks themselves trustworthy.

- [x] H1: the derived artifacts rebuild deterministically and the PDFs carry no build-time timestamp
  CHECK: python3 checks/check20_determinism.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=e33507d5229ae1c999cdfa7ba136cce50911f5d30262ca61d4d795005056f6cc; exit=0; EXPECT=matched; output-sha256=4d3fcabc003da4b189159674840471ca56620a7ccfbc73aba1bb060b865e5032; output-bytes=230; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries

- [x] H1b: two builds of the interactive PDF are byte-identical
  CHECK: python3 checks/check28_byteidentical.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=12c72bfa2b101d1f708858da7a9d0bfc72540e94e29f44a9da70d9ec3676b671; exit=0; EXPECT=matched; output-sha256=cbdcc342d63c0519940dee4a0abac0a94de6d3668c414465b0fb6d6bc384e254; output-bytes=65; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries

- [x] H2: the package is a valid BagIt bag, with the non-redistributable inputs recorded in fetch.txt and the tag files themselves checksummed
  CHECK: python3 checks/check21_bagit.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=d5bf28d3ef08003c892719b30eb3cd12502595b3d695483d999d31f4d7f2f008; exit=0; EXPECT=matched; output-sha256=8a4273a01f3ee5b2c51ddce7799a8984b3a58e84e4144f0b77c686dc78d64434; output-bytes=628; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries

- [x] H3: no claim in the documentation may drift from the artifacts it describes
  CHECK: python3 checks/check22_docs.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=09a6179289c41ca3adbfd2f7e72f66a89dd349570bcf754b31cb84d40c8022c0; exit=0; EXPECT=matched; output-sha256=2e7d604610dc25bf6b86d64dc3ef7791487a003940480bda9059c626cf2cb8f3; output-bytes=145; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries

- [x] H4: every absence assertion has a negative control that proves the detector can report presence
  CHECK: python3 checks/check23_controls.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=ce2bd3185cf9096571b68684855d9ee32267d15dbfc8e9dda930645abd863afb; exit=0; EXPECT=matched; output-sha256=28e249ed04988b190ca63ef5314448a79b3c376a7447f2dbe8796224518103be; output-bytes=820; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries

- [x] H9: no link points at a file, asserted on the PDF action dictionary rather than a viewer-level enum
  CHECK: python3 checks/check27_actions.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=78ec05d430fa28f763616304c311faf3a6584f78fd4d97b192d8d32e4a64ee93; exit=0; EXPECT=matched; output-sha256=ffac7c637e1af20c806d53934d2b376242aa2ee7e64715c1e9c64e1d55b82e68; output-bytes=296; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries

- [x] H5: metamorphic relations hold across the pipeline where no oracle exists
  CHECK: python3 checks/check24_metamorphic.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=55404a4ff67989803f337e9919f7be0ea1cac529166ab5e023ffe49dc7baa737; exit=0; EXPECT=matched; output-sha256=3e995aa5ecb5014b8667e30ebf0a25a12536b384e20c5756ea7fccfd3b15426c; output-bytes=274; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries

- [x] H6: parser and emitter invariants hold under generated input (property-based)
  CHECK: python3 -m pytest -q checks/test_properties.py
  EXPECT: passed
  EVIDENCE: automatic-evidence=v1; definition-sha256=1d92f17ec18f088eb591e845188276c2383397b2069c87d563abaeaf7593ddd6; exit=0; EXPECT=matched; output-sha256=0834674c4b256ace81a8ae319d32c06a79a7caca9fef6a46a455231c28571d02; output-bytes=98; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries

- [x] H7: assertions compare canonical forms, so a legitimate representation change cannot fail a check
  CHECK: python3 checks/check25_normalisation.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=cc0b6bdb6c91848be2f458677bb3d4be6b4e0ce4bfd1e383ffb52eab69d7b1a0; exit=0; EXPECT=matched; output-sha256=5c71062e66c9729fae0ecf4bcdca344d12224c203fdd60dfd65d680730b45deb; output-bytes=632; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries

- [x] H8: the package carries machine-readable provenance and a signed statement of which checks passed on which artifact digests
  CHECK: python3 checks/check26_provenance.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=7f4714cd8df99a1d95e7055390de71bcef75a1b9aaea41d80e3873108bcc357f; exit=0; EXPECT=matched; output-sha256=8c61166876de73ebc8a28619147604bb9494cb95fb33d32f7a4b67f0a0546ab0; output-bytes=467; shell=/bin/sh; cwd=/home/claude/harden; path=2d5a7faa1724/9 entries
