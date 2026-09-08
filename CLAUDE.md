# OBC document graph — working rules

This is advisory context. Anything that MUST hold is a hook in `.claude/hooks/` and a deny in `.claude/settings.json`; CLAUDE.md cannot block an action.

## What this is
The 2024 Ontario Building Code Compendium as a document graph: 27,421 nodes, 29,952 typed edges, zero dangling. SQLite emitters with FTS5 + trigram + closure table + 2,749 article vectors. Packaged as a BagIt bag with RO-Crate and in-toto. The two source PDFs are Crown copyright and fetch-only — never read them by path, never redistribute them.

## How work happens
- `orchestration/tracks.yaml` is the DAG. `python3 orchestration/schedule.py` says what is ready; do not type a status the graph contradicts.
- Every track follows `orchestration/PROTOCOL.md`: seven steps, ten rules. The `obc-seven-step-cycle` skill walks it.
- Verification machinery — `harden/checks/`, `*/checks/`, `ci/`, `gates/`, hooks — is read-only during a track. Propose changes in the audit addendum.
- A ratio gate without a registered H10 mutation is void. `write-h10-control` skill.
- Regenerate before committing: `bash ci/regenerate.sh && touch .regen.stamp`. Order matters.
- Never load the graph into context. Query it: `mcp__obc__*` tools, resources `obc://capabilities`, `obc://provision/{id}`, `obc://gate-board`, `obc://tracks`.

## What the graph cannot answer
Read `obc://capabilities` — the `cannot` list is computed from the database with the SQL shown. Today: applicability, objectives, in-force dates, compliance, meaning-based search (until G1), 44 heading-only notes (until B3). A confident answer to any of these is a hallucination by construction.

## Four decisions require a human
DEC1 assist-vs-judge · DEC2 external exposure · DEC3 hub token cap · DEC4 building official. Ask; never assume. The `decision-guard` hook blocks editing them out of the DAG.

## Citation grammar
`B/9/9.32.3.8` = Division B, Part 9, Article 9.32.3.8. Relative references (`Sentence (1)`) resolve only against their enclosing Article. Italic terms are defined terms; never reason over a provision without its definitions. `obc-citation-grammar` skill.

## Honesty in reporting
Every number cites the check that produced it. Corrections go beneath the finding they correct; earlier audit revisions are never edited. "Green with a real digest proves the check ran. It proves nothing else."
