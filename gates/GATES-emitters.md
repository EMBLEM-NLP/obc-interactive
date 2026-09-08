# Gates: emitters (G16)

OWNS: emit_common.py, stage15_sqlite.py, stage16_markdown.py, stage17_html.py, checks/**, out/**

Scope: emit SQLite, Markdown and accessible HTML from the merged document graph,
carrying a stable permalink, a currency stamp and the licence terms into every
output, per the design review.

- [x] E1: SQLite answers the three queries the model was built for, ranks and highlights, and finds clause numbers
  CHECK: python3 checks/check16_sqlite.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=c8a4b3f5f02aa4361a91a9eabd933b395cdb59a2f4c1ca4494a71b0f30da3f65; exit=0; EXPECT=matched; output-sha256=f439f517dade0c9f71cd4e8e1ab895045c4c40ec53be3e599c010f566b9adae4; output-bytes=558; shell=/bin/sh; cwd=/home/claude/emit; path=2d5a7faa1724/9 entries

- [x] E2: Markdown and HTML carry front matter, literal designators, HTML tables, and pass the mechanical WCAG structure checks
  CHECK: python3 checks/check17_emitters.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=4de2dce600818c64ccaaa78cac2c9bb2487a522610e9f51d8a78a0033680dbcb; exit=0; EXPECT=matched; output-sha256=a4b5f35d713c024854839c20b6d5e5fb78291dfd5cde7714fc9bb0a5a97fd03c; output-bytes=230; shell=/bin/sh; cwd=/home/claude/emit; path=2d5a7faa1724/9 entries

- [x] E3: every emitter carries the same permalink, currency stamp and licence text from one source
  CHECK: python3 checks/check18_identity.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=cbd146d114e80aae62dc485c71e3f1a32e5e9f2f7a4d41049879d7440dc7b47c; exit=0; EXPECT=matched; output-sha256=ad94bf4165c60a7f15d5e4fa015cd072a9bf29d06caad7e67fa8403bab291541; output-bytes=364; shell=/bin/sh; cwd=/home/claude/emit; path=2d5a7faa1724/9 entries

- [ ] E4: WCAG items that no command can decide - contrast, focus order, alt-text quality, screen-reader table reading - are reviewed by a person
  EVIDENCE: pending

- [x] E5: the delivered zip verifies against its own manifest and its contents open
  CHECK: python3 checks/check19_package.py
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=a74be34f5e8eeddf5a5bc0918b1d9d44856908914de931f4ed62db3b6408eb4c; exit=0; EXPECT=matched; output-sha256=b1af19b43bec6dbd72c48f4a5478c194f90a739e7b389f10e35ef74f2a851885; output-bytes=401; shell=/bin/sh; cwd=/home/claude/emit; path=2d5a7faa1724/9 entries

ABANDON: E4 No screen reader, contrast analyser or human reviewer is available in this environment. The mechanical WCAG 2.2 structure checks in E2 pass (lang, title, skip link, landmarks, non-skipping heading order, table captions, id/headers on merged-cell tables, descriptive link text), but conformance cannot be claimed without manual review. Handoff: run axe or WAVE plus a NVDA/VoiceOver pass over out/html, focusing on the merged-cell tables in Part 11 and Appendix A, and supply long descriptions for figure assets before publication.
