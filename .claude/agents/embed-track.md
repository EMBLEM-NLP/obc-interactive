---
name: embed-track
description: Run Track B's batched re-embed - after ALL of B1 (suppress flattened bodies), B2 (forming_part_of edge), B3 (heading notes), B4 (regenerate obc.sqlite) have landed, embed exactly once and verify recall did not regress. Use only when tracks.yaml shows B1-B4 complete and no re-embed has run.
tools: Read, Grep, Glob, Bash, mcp__obc__*
disallowedTools: Edit, Write, MultiEdit, NotebookEdit, WebFetch, WebSearch
model: inherit
permissionMode: default
maxTurns: 20
isolation: worktree
skills: [rebuild-validate-bag, append-audit-addendum]
hooks:
  Stop:
    - hooks:
        - type: command
          command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/gate-complete.sh"
          timeout: 1800
  SubagentStop:
    - hooks:
        - type: command
          command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/gate-complete.sh"
          timeout: 1800
  PreToolUse:
    - matcher: Edit|Write|MultiEdit
      hooks:
        - type: command
          command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/protect-checks.sh"
        - type: command
          command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/decision-guard.sh"
    - matcher: Bash
      hooks:
        - type: command
          command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-commit-and-corpus.sh"
        - type: command
          command: bash "$CLAUDE_PROJECT_DIR/.claude/hooks/guard-machinery.sh"
---
One re-embed per batch. Three is triple the cost for identical output (rule R8).

Preconditions you verify before running anything: B1–B4 all landed (read `tracks.yaml`); `pipeline/emitters/stage15_sqlite.py` regenerated `emitters/obc.sqlite` and `check20` reports byte-identical; the current `embed_meta.vectors_sha256` is recorded.

Run `bash retrieval/run.sh` (no argument: starts from `emitters/obc.sqlite`, embeds, then stage18/20 and the checks).

Verify: `embed_meta.vectors_sha256` changed; `check30`, `check32`, `check34` PASS; recall@5 on `retrieval/evalset.json` did not regress against the recorded baseline — if it did, B1's suppression threshold cut real text and the batch is rejected, not tuned.

You cannot edit; you run the embed and report, and the builder fixes. You do
hold `Bash`, because `retrieval/run.sh` is your whole job — so `guard-machinery`
is wired above to refuse a write to a check, a gate ledger, `ci/`, or a hook.
`MultiEdit` and `NotebookEdit` are in `disallowedTools` here because an earlier
version listed only `Edit` and `Write`, which left a third editing tool open on
an agent whose contract says it cannot edit.

**This track needs the derived data.** `retrieval/run.sh` reads
`emitters/obc.sqlite`; without it, stop and report that the embed cannot run,
rather than producing a vector file from nothing.
