#!/usr/bin/env python3
"""Shared hook-input parser. FAIL CLOSED.

Usage in a hook:   eval "$(python3 "$(dirname "$0")/_input.py")"
Exports HOOK_OK=1 plus HOOK_FILE, HOOK_CMD, HOOK_NEW, HOOK_STOP_ACTIVE as shell
variables. If stdin is not parseable JSON, exports HOOK_OK=0 and a reason; the
calling hook must then exit 2.

Why Python and why fail-closed: the first version used jq, jq was not installed,
every guard read an empty string and allowed everything. An enforcement hook
that cannot read its input must refuse, not wave the action through.
"""
import json, sys, shlex
try:
    d = json.load(sys.stdin)
    ti = d.get("tool_input") or {}
    out = {
        "HOOK_OK": "1",
        "HOOK_FILE": ti.get("file_path") or ti.get("path") or "",
        "HOOK_CMD": ti.get("command") or "",
        "HOOK_NEW": ti.get("new_string") or ti.get("content") or "",
        "HOOK_STOP_ACTIVE": "1" if d.get("stop_hook_active") else "0",
        "HOOK_TOOL": d.get("tool_name") or "",
    }
except Exception as e:
    out = {"HOOK_OK": "0", "HOOK_REASON": f"hook input not parseable: {type(e).__name__}"}
for k, v in out.items():
    print(f"export {k}={shlex.quote(str(v))}")
