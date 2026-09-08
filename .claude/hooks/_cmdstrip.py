#!/usr/bin/env python3
"""Decide whether a shell command actually RUNS a git-commit invocation.

Reads the command on stdin. Prints COMMIT or NONE and exits 0. Any internal
error exits non-zero so the calling hook can fail closed.

Why this exists
---------------
guard-commit used to grep the whole command string. That treats DATA as CODE:
writing a message file with a heredoc whose body mentions the verb was refused
as though it were a real commit. Observed 2026-09-08.

The obvious fix - strip quoted spans before matching - is worse than the bug.
    bash -c 'git<SP>commit -m x'
is a real commit living entirely inside single quotes, so a stripper would
wave through exactly the evasion a guard exists to catch.

So this does neither. It lexes the command the way a shell would and asks only
whether the verb appears in COMMAND POSITION:

  1. heredoc bodies are removed first - they are data by construction
  2. the remainder is split on ; && || | and newline, respecting quotes
  3. each segment is shlex-split, so `echo "git<SP>commit"` is one argument
     token and never looks like a command
  4. bash -c / sh -c payloads are re-analysed recursively, so wrapping the
     command in quotes does not evade the guard
  5. anything that cannot be lexed or nests too deep returns COMMIT, because a
     guard that cannot read its input must refuse
"""
import re
import shlex
import sys

HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
OPS = {";", "&&", "||", "|", "&", "(", ")", "\n"}
SHELLS = {"bash", "sh", "zsh", "dash", "ksh"}
# git global options that take a separate value before the subcommand
GIT_OPTS_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--exec-path"}


def strip_heredocs(cmd):
    """Drop heredoc bodies. Their content is data, never a command."""
    lines = cmd.split("\n")
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = HEREDOC.search(line)
        out.append(HEREDOC.sub("", line))
        if m:
            term = m.group(2)
            i += 1
            while i < len(lines) and lines[i].strip() != term:
                i += 1
        i += 1
    return "\n".join(out)


def newlines_to_separators(text):
    """Turn newlines OUTSIDE quotes into `;`, leaving quoted ones alone.

    Lexing line by line looked simpler and was wrong: a command ending in a
    multi-line `python3 -c "..."` argument has an unterminated quote on its
    first line, shlex raised, and this returned COMMIT for a command with no
    commit anywhere in it. Fail-closed is the right direction for a guard and
    still the wrong answer, so the newline handling is done here instead.
    """
    out = []
    quote = None
    i = 0
    while i < len(text):
        ch = text[i]
        if quote:
            if ch == "\\" and quote == '"' and i + 1 < len(text):
                out.append(ch); out.append(text[i + 1]); i += 2; continue
            if ch == quote:
                quote = None
            out.append(ch)
        else:
            if ch in "'\"":
                quote = ch
                out.append(ch)
            elif ch == "\\" and i + 1 < len(text):
                out.append(ch); out.append(text[i + 1]); i += 2; continue
            elif ch == "\n":
                out.append(";")
            else:
                out.append(ch)
        i += 1
    return "".join(out)


def segments(text):
    """Split a command into command segments, honouring quotes."""
    lex = shlex.shlex(newlines_to_separators(text), posix=True, punctuation_chars=True)
    lex.whitespace_split = True
    toks = list(lex)
    segs, cur = [], []
    for t in toks:
        if t in OPS or (t and set(t) <= {";", "&", "|"}):
            segs.append(cur)
            cur = []
        else:
            cur.append(t)
    segs.append(cur)
    return segs


def git_subcommand_is(seg, verb):
    """True when seg is a git invocation whose subcommand is `verb`."""
    i = 1
    while i < len(seg):
        t = seg[i]
        if t in GIT_OPTS_WITH_VALUE:
            i += 2
            continue
        if t.startswith("-"):
            i += 1
            continue
        return t == verb
    return False


def has_commit(cmd, depth=0):
    if depth > 3:
        return True
    text = strip_heredocs(cmd)
    if text.strip():
        try:
            segs = segments(text)
        except ValueError:
            return True
        for seg in segs:
            if not seg:
                continue
            j = 0
            while j < len(seg) and "=" in seg[j] and not seg[j].startswith("-"):
                j += 1          # skip VAR=value prefixes
            if j >= len(seg):
                continue
            head = seg[j:]
            if head[0] == "git" and git_subcommand_is(head, "commit"):
                return True
            if head[0] in SHELLS and "-c" in head:
                k = head.index("-c")
                if k + 1 < len(head) and has_commit(head[k + 1], depth + 1):
                    return True
    return False


def main():
    try:
        print("COMMIT" if has_commit(sys.stdin.read()) else "NONE")
    except Exception as e:                       # noqa: BLE001
        print(f"_cmdstrip failed: {type(e).__name__}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
