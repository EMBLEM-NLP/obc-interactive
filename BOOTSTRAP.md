# First prompt for Claude Code

Paste the block below as your **first** message after opening this repo in Claude Code.
Do not start Track A4 first. This prompt is step 5 of `MIGRATION.md`: it proves the
enforcement layer actually fires under the host. Every hook here was verified as a
script, never as invoked by Claude Code — that is the one thing this establishes.

---

```
Read MIGRATION.md, CLAUDE.md, and orchestration/PROTOCOL.md before doing anything.

This is a verification smoke test, not a work track. Do these six things IN ORDER and
report what happened at each step. Several are SUPPOSED to fail — a step that succeeds
when it should be blocked is the finding, and you should stop and say so.

1. Confirm the environment:
   pip install -r requirements.txt
   python3 ci/test_hooks.sh              # expect RESULT: PASS, 19 cases
   python3 orchestration/schedule.py     # expect A4/C/E/MAINT ready, 4 decisions pending
   python3 ci/run_gates.py               # expect 0 failed, 1 known-review (G7), some skips

2. Confirm the MCP server is connected. Call obc_capabilities. Report the `cannot` list
   and the SQL evidence behind each entry. These are computed from the database, not typed.

3. Try to edit harden/checks/check35_controls.py — add a comment line.
   EXPECT: blocked by the protect-checks hook. Report the exact message.
   If this succeeds, STOP. The enforcement layer is not active and nothing else is valid.

4. Try to change FRULES status to "ready" in orchestration/tracks.yaml.
   EXPECT: blocked by decision-guard — DEC1 requires a human. Report the message.

5. Run: git add -A && git commit -m "smoke test"
   EXPECT: blocked by guard-commit — no .regen.stamp, or files edited after the last
   ci/regenerate.sh. Report the message. Then run `bash ci/regenerate.sh && touch
   .regen.stamp` and commit again; it should now succeed.

6. Append one line to orchestration/PROTOCOL.md under "Rules", recording that hooks were
   observed firing under Claude Code on <today's date>, with which hooks fired. Then end
   your turn.
   EXPECT: the Stop hook runs check35 and the full gate board (~4 minutes) before allowing
   the turn to end. If the board is red it will refuse and tell you why.

Then write AUDIT-rev6.md with four sections — WHAT MOVED, WHAT DID NOT, WHAT BROKE,
WHAT WAS FOUND — following the append-audit-addendum skill. In WHAT WAS FOUND, state
plainly whether each of the four hooks fired under the host, and update
orchestration/tracks.yaml ENFORCE.evidence to replace "host unverified" only if all four
were observed. If any hook did not fire, that is the finding; do not soften it.

Do not start Track A4. Do not resolve any decision in tracks.yaml decisions_pending.
```
