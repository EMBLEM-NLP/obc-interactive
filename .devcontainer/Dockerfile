# Reproducible environment for running the gate board and Claude Code sessions.
# The pip and huggingface caches are volumes so torch and the sentence-transformers
# weights survive rebuilds - without that, three gates SKIP or the container spends
# minutes re-downloading on every start.
FROM mcr.microsoft.com/devcontainers/python:1-3.12-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
      git git-lfs jq ripgrep sqlite3 poppler-utils ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN npm install -g @anthropic-ai/claude-code
ENV PYTHONHASHSEED=0 SOURCE_DATE_EPOCH=1737072000 TZ=UTC
WORKDIR /workspace
