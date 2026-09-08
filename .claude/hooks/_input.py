#!/usr/bin/env python3
"""Shared hook-input parser. FAIL CLOSED.

Usage in a hook:   eval "$(python3 "$(dirname "$0")/_input.py")"
Exports HOOK_OK=1 plus HOOK_FILE, HOOK_CMD, HOOK_NEW, HOOK_STOP_ACTIVE,
HOOK_TOOL and HOOK_RAW as shell variables. If stdin is not parseable JSON,
exports HOOK_OK=0 and a reason; the calling hook must then exit 2.

Why Python and why fail-closed: the first version used jq, jq was not
installed, every guard read an empty string and allowed everything. An
enforcement hook that cannot read its input must refuse, not wave the action
through.

Why HOOK_RAW: a hook reads stdin exactly once, and this parser consumes it,
so a downstream helper cannot re-read the payload. HOOK_RAW carries the whole
original payload base64-encoded, so a guard that needs fields this parser does
not flatten - old_string, replace_all, a MultiEdit edits array - can recover
them without a second read. Added when decision-guard was found to be judging
`new_string` in isolation, which no partial Edit ever fills in usefully.
"""
import base64, json, sys, shlex

try:
    raw = sys.stdin.read()
    d = json.loads(raw)
    ti = d.get("tool_input") or {}
    out = {
        "HOOK_OK": "1",
        "HOOK_FILE": ti.get("file_path") or ti.get("path") or "",
        "HOOK_CMD": ti.get("command") or "",
        "HOOK_NEW": ti.get("new_string") or ti.get("content") or "",
        "HOOK_STOP_ACTIVE": "1" if d.get("stop_hook_active") else "0",
        "HOOK_TOOL": d.get("tool_name") or "",
        "HOOK_RAW": base64.b64encode(raw.encode("utf-8")).decode("ascii"),
    }
except Exception as e:
    out = {"HOOK_OK": "0",
           "HOOK_REASON": f"hook input not parseable: {type(e).__name__}",
           "HOOK_RAW": ""}
for k, v in out.items():
    print(f"export {k}={shlex.quote(str(v))}")
