# Gates: remediation

OWNS: stage18_definitions.py, stage20_modality.py, checks/**, obc_context.py,
      run.sh, GATES-remediation.md

Scope: close the two R-gates that do not hold as stated, restore definition
granularity, persist modality, and add the control discipline that would have
caught all three defects found so far.

Supersedes: R4 in GATES-retrieval.md, which is replaced by R4a/R4b/R4c.
REMOVED: check33_completeness.py — its metric is arithmetically incapable of
falling below its floor (11680/11680 = 100.0000% corpus-wide, 0 articles below
threshold), because `bundle()` unions in the `refs | terms` set it is scored
against. Retained in history, not in the pipeline.

All ratio gates below run in `--all-articles` mode. Corpus mode gates; eval
mode is convenience. Every corpus run so far has found something the
50-question eval set missed.

- [x] D1: definition blobs are split into individual terms, and term edges resolve to the specific definition
  CHECK: python3 check29_definitions.py --db obc-mod.sqlite
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=d3c62efe11d8264f45aadcf8d08c910837de4dfdb7bbe9a4f85c2e41a3dc9dfc; exit=0; EXPECT=matched; output-sha256=de99a63df2058119c084df676649c3f70f5fccae148a1bce7d1e4d90f552796f; output-bytes=297; shell=/bin/sh; cwd=remediation

- [x] R4a: expansion reaches every dependency of a non-hub provision
  CHECK: python3 check33b_completeness.py --db obc-mod.sqlite --all-articles
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=fb384ae016510f338b220a83701acbfae48d5a7a8c240f24e497a060f96165a4; exit=0; EXPECT=matched; output-sha256=b5bb1e8630c347ce35c9a59006dc1d3f7f7abbcaf62c0a80223befa87c4f9c0d; output-bytes=735; shell=/bin/sh; cwd=remediation

- [x] R4b: the rendered, budget-trimmed bundle delivers what expansion reached
  CHECK: python3 check33b_completeness.py --db obc-mod.sqlite --all-articles
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=fb384ae016510f338b220a83701acbfae48d5a7a8c240f24e497a060f96165a4; exit=0; EXPECT=matched; output-sha256=b5bb1e8630c347ce35c9a59006dc1d3f7f7abbcaf62c0a80223befa87c4f9c0d; output-bytes=735; shell=/bin/sh; cwd=remediation

- [x] R4c: a delivered definition is that term's own definition, not the clause containing it
  CHECK: python3 check33b_completeness.py --db obc-mod.sqlite --all-articles
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=fb384ae016510f338b220a83701acbfae48d5a7a8c240f24e497a060f96165a4; exit=0; EXPECT=matched; output-sha256=b5bb1e8630c347ce35c9a59006dc1d3f7f7abbcaf62c0a80223befa87c4f9c0d; output-bytes=735; shell=/bin/sh; cwd=remediation

- [x] R8: deontic modality is persisted on every text-bearing leaf
  CHECK: python3 stage20_modality.py --in obc-defs.sqlite --out /tmp/g_mod.sqlite
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=82c3cf69ca7daa33dbe3aaed9c022516289f2bf4c3fa5efe378b726ba23409e0; exit=0; EXPECT=matched; output-sha256=1817ff5d5ef3fc8b27b9e83bb5c2e618d4249af155980b39521fe9f7ead03013; output-bytes=285; shell=/bin/sh; cwd=remediation

- [x] H10: every gate reporting a ratio has a mutation that drives it below its floor
  CHECK: python3 check35_controls.py --db obc-mod.sqlite
  EXPECT: RESULT: PASS
  EVIDENCE: automatic-evidence=v1; definition-sha256=959724e07fa9b63436c5bf1b111cd5f6f92190271ab9dec60a09cbd5fa8f6664; exit=0; EXPECT=matched; output-sha256=2918d4f263202a689b87d4442eba254de68830015ab62739a3ebaafa57d4f3ef; output-bytes=742; shell=/bin/sh; cwd=remediation

