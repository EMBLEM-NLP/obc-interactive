# check4_capture.py — superseded 2026-09-07

Its metric could not fail. It compared corpus-wide character multisets; the
tree carries 4,697,394 characters against 2,742,659 on the page, a 71% surplus
from index entries, the Act, notes and headings. Blanking 100% of sentence text
(7,667 sentences, ~1.39M characters) left "orphaned" at 0.140%, under the 0.5%
floor. Found by the H10 mutation registry in harden/checks/check35_controls.py.

Replaced by check4b_capture.py, which compares per page. On the untouched build
it reports 0.039% orphaned (1,054 characters, 23 pages) — a real number — and
fails under the same mutation. Same copy in pipeline/checks/.
