# Gates: semantic retrieval

OWNS: checks/**, stage19_embed.py, lib/**, out/**, GATES.md

Scope: add article-level semantic recall to the existing exact and lexical
layers, fused by Reciprocal Rank Fusion, and prove the fusion beats either
layer alone rather than assuming it.

- [x] R1: every article node has a deterministic contextual embedding, stored in the same database file
  CHECK: python3 checks/check30_embeddings.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=d205548f241702362886d35420cc9aab8ec4018e3f72d0ef8bff45a478f7f629; exit=0; EXPECT=matched; output-sha256=a4505317469af2b0c775e4b41dcd4496ee39aebdc2131cc81fc208f89adac90d; output-bytes=286; shell=/bin/sh; cwd=/home/claude/retrieval; path=2d5a7faa1724/9 entries

- [x] R2: the evaluation set is real, provenanced, and hand-checked, not generated from the answers
  CHECK: python3 checks/check31_evalset.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=39416218ad2913547c23e800410c25e3e3cac703820d326eda45a2de1670380d; exit=0; EXPECT=matched; output-sha256=8e722c5c48f137539404d2663ec363778c1436cc864b2adb5340a74301b3b8bd; output-bytes=232; shell=/bin/sh; cwd=/home/claude/retrieval; path=2d5a7faa1724/9 entries

- [x] R3: hybrid retrieval beats both FTS5 alone and vectors alone on recall@5, and the vector layer earns its place on queries with no lexical overlap
  CHECK: python3 checks/check32_fusion.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=307b3809f7a383d00c629de33f1b89038c50ecc9a1a046c257bf79c785460ac6; exit=0; EXPECT=matched; output-sha256=83344684e66dbf754aee2975ae7463abb12ca51dc03366fcc7a52197411bf0f2; output-bytes=773; shell=/bin/sh; cwd=/home/claude/retrieval; path=2d5a7faa1724/9 entries

- [~] R4: SUPERSEDED 2026-09-07 — retrieval returns complete mandatory context.
  check33_completeness.py's metric is arithmetically incapable of failing:
  bundle() unions in the exact refs|terms set dependencies() measures against
  it, so dep & bundle(nid) == dep for every node (11680/11680 = 100.0000%
  corpus-wide, independent of data). Moved to retrieval/checks/superseded/.
  Replaced by R4a/R4b/R4c in gates/GATES-remediation.md, each carrying a
  mutation in harden/checks/check35_controls.py that must drive it below
  its floor. Do not re-enable this line as written.
  CHECK: python3 checks/check33_completeness.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=8ab780bbf29acfa29896bac46fd5323fd64152309645a34e380393ef7df5fc9d; exit=0; EXPECT=matched; output-sha256=0d6014a626a9c072fbfa484b71121328a3fa83a02ca972a18ce283fad7401a32; output-bytes=760; shell=/bin/sh; cwd=/home/claude/retrieval; path=2d5a7faa1724/9 entries

- [x] R5: a negative control proves the eval harness can fail — a deliberately broken index must score near zero
  CHECK: python3 checks/check34_control.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=2f6f910d713675be48553013e9401471c5d4e6075b613ece52723684d1244bee; exit=0; EXPECT=matched; output-sha256=31cd05ef37fe993ea011d463448a5e7cc52c033bac90a5266badc5dd633bb26c; output-bytes=476; shell=/bin/sh; cwd=/home/claude/retrieval; path=2d5a7faa1724/9 entries
