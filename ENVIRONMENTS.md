# Where this repository runs

Short answer to "is this for the Claude Code cloud container via GitHub?" — **partly, and not for the part that matters.** CI runs on GitHub. Track execution does not run in a cloud sandbox.

| activity | environment | why |
|---|---|---|
| Step-5 hook smoke test | **local CLI**, then devcontainer | the one thing no hosted surface can validate for you |
| Track execution (A4, B, C, E) | **local CLI or devcontainer** | worktree subagents, stdio MCP server, torch, 4-minute board |
| The 41-gate board in CI | **GitHub Actions, plain Python steps** | deterministic; it needs no agent |
| PR-comment summary | **`claude-code-action@v1`, agent mode** | summarises a board it did not produce |
| Browser / phone delegation | **not supported** | see below |

## Why not Claude Code on the web

Three reasons, in order of severity.

1. **Git LFS is broken in the cloud sandbox.** The session's GitHub proxy rejects the LFS batch endpoint with `Proxy error: invalid git path` (anthropics/claude-code#25043; recurring as #60593). This repo no longer uses LFS *because of that finding* — but it means any LFS-based approach is out, and it is why the data is fetched and hash-verified instead.
2. **The data is 315 MB against a 30 GB disk and a ~5-minute setup-script budget**, with `sentence-transformers` pulling torch. Survivable with caching, but the sandbox has no shell for you to intervene when it isn't.
3. **The Stop hook runs a ~4-minute gate board.** The command-hook default timeout is 600 s so it fits, but cloud session inactivity limits are undocumented. Designing an unattended cloud run around an unpublished timeout is the kind of assumption this project does not make.

Hooks, `.mcp.json`, skills and subagents *are* honoured in cloud sessions — they are cloned from the repo. The blocker is data and duration, not fidelity.

## If you want hosted delegation later

A **self-hosted cloud environment** (Team/Enterprise) runs the same product on your own runners, so LFS, secrets and egress are yours. That is the only cloud path that can carry this repo.

## What each environment needs

- **local**: `pip install -r requirements.txt`, then `bash ci/fetch_data.sh` once.
- **devcontainer**: nothing — `postCreateCommand` installs deps and runs the hook tests. Fetch data once inside.
- **GitHub Actions**: secrets `OBC_DATA_URL`, `OBC_PDF_URL_V1`, `OBC_PDF_URL_V2`, `ANTHROPIC_API_KEY`. No `lfs: true` on checkout — there are no LFS objects.
- **cloud web**: not supported for gate-running sessions.

---

Unofficial derived work. © King's Printer for Ontario, 2024. Reproduced with permission.
