# Gates: Volume 1 complete

OWNS: checks/**, out/**, GATES.md

Scope: the 2024 Building Code Compendium Volume 1 is parsed into a verified
document model and rebuilt as an interactive PDF that loses nothing relative to
the previous hand-patched build.

- [x] G1: every glyph the source renders is captured in the page inventory
  CHECK: python3 checks/check0_coverage.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=3e1e8db92ed1e0732754091a7484c0f04ba4c4e346e983745605e8b71d9cf902; exit=0; EXPECT=matched; output-sha256=2cff4c59c9199642b9530fb54e6fab54b28c569ffe76da94f04d0520d55100f9; output-bytes=245; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G2: every table and figure the document declares is detected as a region
  CHECK: python3 checks/check1_regions.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=105df8249507a949893deed157dd1e29c0d4a56629557230a4f398e859f72db0; exit=0; EXPECT=matched; output-sha256=5dfe6e0bc7c738c3602a7e9cc1d002d962cc695b59e84ce7f1e0635ea03b1308; output-bytes=321; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G3: the structure detector and the printed contents pages agree in both directions
  CHECK: python3 checks/check2_headings.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=8f57b34f034f258983eb284caaba920233138254bdd0c6887a3d6e74aff04126; exit=0; EXPECT=matched; output-sha256=786436e6d7857ce69a62224f4230523446e327447c26e17afd687b14a10740b0; output-bytes=1468; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G4: provision numbering runs without an unexplained gap anywhere in the tree
  CHECK: python3 checks/check3_continuity.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=10824042256f2fba1cca376fd108c24f967cae1c7dfe53042c7b98c840b94a0f; exit=0; EXPECT=matched; output-sha256=1aef5377357cb9352af3d160a310d2747fb288ef78227c8e4f883abbe712b8b4; output-bytes=65; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [~] G5: SUPERSEDED 2026-09-07 — content text lands in the node tree rather than being dropped
  The check behind this gate, check4_capture.py, could not fail: it compared
  corpus-wide character multisets with a 71% surplus, and blanking 100% of
  sentence text left orphaned at 0.140% < 0.5%. The evidence digest below is
  real — the check ran and exited 0 — and proves nothing about capture.
  Replaced by check4b_capture.py (per-page), controlled in check35. Do not
  re-enable this line as written.
  CHECK: python3 checks/check4b_capture.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=fb69210e9f948ea1edfe1a6fc53104bd3ce316165bf86649f991bfc61d6697d1; exit=0; EXPECT=matched; output-sha256=a994add824da28c6c7d05a3771bf0b445bd0ed9ed888aae1cad864d4b7b05c1c; output-bytes=113; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G6: table cells tile their region and hold their text
  CHECK: python3 checks/check5_tables.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=24b02bc694c82ddf1a9f60186619d8b6a5a42a7d2740e1eef33c02f542cf154e; exit=0; EXPECT=matched; output-sha256=4a55d5542bc23ba98a52bbfbf310ea1ec440eb1bcf611c10ec0cc6425c74d9c8; output-bytes=484; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G7: every citation resolves or carries a reason code, with no parse failures
  CHECK: python3 checks/check7_refs.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=586694e0ee9d7b9534e353f7e709e45309bce2b5153670eb654e30ec911db0e6; exit=0; EXPECT=matched; output-sha256=57c307eb869ed0d99fbedfdb750b80a4260fd9046da6ac9e32e1b06632cfd297; output-bytes=390; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G8: the model-built PDF is a strict superset of the hand-patched build
  CHECK: python3 checks/check8_build.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=5a4ee0be9e5236192f9c63ad28decd95ccf53f004e1d7cc742140ab70e8c3be6; exit=0; EXPECT=matched; output-sha256=507f43934fe77b90e04301fbe045ed007f2a5fef4d487f8d1e68be4c6f03638f; output-bytes=603; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G9: the absence assertions in G8 can actually detect the defects they deny
  CHECK: python3 checks/control_negative.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=8110c82785e1ca5478c9ebae8a389153e6b7247668266096089ea4fa2135b589; exit=0; EXPECT=matched; output-sha256=13edfaaddf4c182512fcff9885a6dc3e508b2d8a5cb7e387960c1a7d216730c4; output-bytes=99; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G10: every amendment marker is attached to the provision it annotates
  CHECK: python3 checks/check9_amendments.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=81a4cea53b333d79ab2ca93278b69382762cf2e802ef3dc5bdd06deb6e1f23f6; exit=0; EXPECT=matched; output-sha256=6e915b3f4fe9c825c76f9d0afd57540473e94d15b4969a9687e9c54b1e8599b8; output-bytes=605; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G11: the Index is parsed into entries with resolving citations
  CHECK: python3 checks/check10_index.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=8e3bc31c39c082120e53c330857079bb2c0f7e34ba253dcc2af5857658ee1c3d; exit=0; EXPECT=matched; output-sha256=464539aefcba10a0a2c454267e0f3a1d2660c3f3318fb4db38e1062299eabae5; output-bytes=246; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G12: the shipped file opens freely, is correctly protected, and keeps its text layer
  CHECK: python3 checks/check11_deliverable.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=8e0438dd38efe3ab8a33ba39b2e43114f5ef295aa2d71aebc808f9c0494ca2a0; exit=0; EXPECT=matched; output-sha256=c719529e4159e3552d3b14a07683cbac54598c184065ba1036699dd9340778d0; output-bytes=366; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G13: figure assets are exported and bound to their captions
  CHECK: python3 checks/check6_figures.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=deca628f087df74150120a1bf8d9fa91d99b929b6964b363218c49b874cf9ce0; exit=0; EXPECT=matched; output-sha256=9c382ef4ae657d03c8a11e4b1eb12671ab54be9b459eca127a07d4913fe2aa14; output-bytes=234; shell=/bin/sh; cwd=/home/claude/obc; path=2d5a7faa1724/9 entries

- [x] G14: the licence terms and modification record are stated for redistribution
  EVIDENCE: manual. /mnt/user-data/outputs/CHANGELOG.md records every modification,
    the known gaps, the verification performed, and quotes the ministry's own terms
    from pp.3-4 of the document, including the required "(c) King's Printer for
    Ontario, 2024. Reproduced with permission." and the commercial-use contact.
    Reviewed against the source pages 3-4 on 2026-09-06.

- [x] G15: references whose targets live in Volume 2 resolve
  CHECK: python3 ../volume2/checks/check14_crossvol.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=7271883aca15e14d8084e158111ea80cb7cabdb3d1ac6ba89298388fba65e585; exit=0; EXPECT=matched; output-sha256=40c5f864313675c4edfe295a9238532036c2203a91a0ce06ec5f2ebc10958a82; output-bytes=308; shell=/bin/sh; cwd=/home/claude/verify/volume2; path=2d5a7faa1724/9 entries
  CWD: ../volume2

- [x] G16: markdown, html and sqlite emitters are written
  CHECK: cd ../emitters && python3 checks/check16_sqlite.py && python3 checks/check17_emitters.py && python3 checks/check18_identity.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=0a4b29218809b0b786a570ba4eb5714041a5aa4054d14fbe99e23ed0997ddce7; exit=0; EXPECT=matched; output-sha256=ece1aa6e5a8ea1b91d721a3be5a7894a70a7b189e8a71cc8cf5f850bc73cf8a2; output-bytes=1152; shell=/bin/sh; cwd=/home/claude/verify/volume1; path=2d5a7faa1724/9 entries
