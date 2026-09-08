#!/usr/bin/env python3
"""Allowlist for a read-only verifier's Bash. Prints ALLOW or DENY: <reason>.

Why this file exists
--------------------
verify-track's specification tried to constrain it by scoping Bash in the agent
`tools` field:

    tools: Read, Grep, Glob, Bash(python3 ci/run_gates.py*), ...

A probe dispatched on 2026-09-08 ran `echo hello > /tmp/verify_probe.txt`, which
is nowhere on that list, and it was permitted with no prompt and no refusal.
Tools-field scoping is NOT enforced by the harness. The same probe confirmed a
PreToolUse hook DOES fire inside a worktree and did refuse a write to a check.
So the allowlist is implemented where enforcement demonstrably happens.

That is the third time in this project a constraint has been written as a
sentence instead of a mechanism, and the second in one day. The first was this
same agent's file claiming "You have no write tools" while granting plain Bash.

Allowed: the commands verify-track's own body tells it to run, plus ordinary
read-only inspection. Everything else is refused - any redirection, any `-c`
payload, any git subcommand that touches the working tree. Refusal is the
default, so a command nobody thought about is denied rather than admitted.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _cmdstrip import segments, strip_heredocs, REDIRECTS  # noqa: E402

READ_ONLY = {
    "cat", "head", "tail", "grep", "rg", "egrep", "fgrep", "ls", "wc", "find",
    "file", "stat", "sort", "uniq", "cut", "diff", "cmp", "echo", "printf",
    "pwd", "dirname", "basename", "date", "tr", "jq", "column", "true", "env",
    "sha256sum", "md5sum", "sha512sum", "nl",
}
PY_SCRIPTS = ("ci/run_gates.py", "orchestration/schedule.py")
PY_DIRS = ("harden/checks/", "retrieval/checks/", "pipeline/checks/", "verify/")
SH_SCRIPTS = ("ci/regenerate.sh", "ci/test_hooks.sh", "verify/verify.sh")
GIT_READONLY = {"status", "diff", "log", "show", "rev-parse", "ls-files",
                "branch", "describe", "worktree", "diff-index", "cat-file"}


def norm(p):
    p = p.replace(os.sep, "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def judge_segment(seg):
    """None if allowed, else the reason it is refused."""
    j = 0
    while j < len(seg) and "=" in seg[j] and not seg[j].startswith("-"):
        j += 1
    seg = seg[j:]
    if not seg:
        return None
    head = os.path.basename(seg[0])
    args = seg[1:]
    if head in ("sed", "awk", "gawk", "perl"):
        if any(a == "-i" or a.startswith("-i") or a == "--in-place" for a in args):
            return head + " in-place editing is a write"
        return None
    if head in READ_ONLY:
        return None
    if head in ("python3", "python"):
        if "-c" in args or "-m" in args:
            return "python3 -c/-m can write anything; not verifiable from the command text"
        target = next((norm(a) for a in args if not a.startswith("-")), None)
        if target is None:
            return "python3 with no script is an interactive interpreter"
        if target in PY_SCRIPTS or any(target.startswith(d) for d in PY_DIRS):
            return None
        return "python3 " + target + " is not one of the scripts this verifier runs"
    if head in ("bash", "sh", "zsh"):
        if "-c" in args:
            return "bash -c payloads are not verifiable from the command text"
        target = next((norm(a) for a in args if not a.startswith("-")), None)
        if target in SH_SCRIPTS:
            return None
        return "bash " + str(target) + " is not one of the scripts this verifier runs"
    if head == "git":
        sub = next((a for a in args if not a.startswith("-")), None)
        if sub in GIT_READONLY:
            return None
        return "git " + str(sub) + " is not a read-only subcommand"
    return head + " is not on the verifier allowlist"


def main():
    text = strip_heredocs(sys.stdin.read())
    try:
        segs = segments(text)
    except ValueError:
        print("DENY: the command could not be lexed, so it cannot be judged")
        return 0
    for seg in segs:
        if any(t in REDIRECTS for t in seg):
            print("DENY: redirection writes a file; this verifier does not write")
            return 0
        reason = judge_segment(seg)
        if reason:
            print("DENY: " + reason)
            return 0
    print("ALLOW")
    return 0


if __name__ == "__main__":
    sys.exit(main())
