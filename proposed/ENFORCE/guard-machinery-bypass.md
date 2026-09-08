# ENFORCE, open item — three ways past `guard-machinery`, none of them exotic

Staged, not applied: the fix is in `.claude/hooks/_cmdstrip.py` / `guard-machinery.sh`
and the cases belong in `ci/test_hooks.sh`, all protected (R13).

## Verified verdicts

Probed by feeding the hook crafted stdin exactly as `ci/test_hooks.sh` does. **No
writes were performed**, and the bypasses were not used to promote anything.

| command | `guard-machinery` |
|---|---|
| `cp x harden/checks/evil.py` | **2 — refused** |
| `cp x /home/user/obc-interactive/harden/checks/evil.py` | **2 — refused** |
| `D=/home/user/obc-interactive; cp x "$D/harden/checks/evil.py"` | **0 — permitted** |
| `cp x ${PWD}/harden/checks/evil.py` | **0 — permitted** |
| `cd harden/checks && cp ../../x evil.py` | **0 — permitted** |

Found while attempting an authorised promotion: a dry-run copy into a scratch
directory, written as `cp … "$D/harden/checks/…"`, was permitted when its literal
equivalent would have been refused.

## Why

`check41._candidates()` expands a path into every suffix of itself **only when
`os.path.isabs(p)`**. The hook lexes the command string before the shell expands
it, so `$D/harden/checks/evil.py` and `${PWD}/harden/checks/evil.py` are not
absolute at that moment: they are tested as one literal string, which matches no
pattern. The third case is different and simpler — the working directory changed,
so the write target really is just `evil.py`, and nothing in the command names a
protected path at all.

The first two are variable indirection. The third needs no trick: it is how a
person would naturally do it.

## What this does and does not mean

It does **not** break the stated security model. `check41`'s own docstring says
prevention here is a convenience and gate **E2** is the guarantee, because no
PreToolUse hook can be sound against an executor that also holds Bash — the same
command that edits a check can disable the hook. All three writes above would be
caught by E2 on the way out, which is the property that actually holds.

What it does mean is that `guard-machinery` is **weaker than its twelve E1 cases
suggest**. Every existing case uses a literal path, so the suite measures the
matcher on exactly the inputs the matcher handles. That is the shape of a control
that tests one direction (AUDIT-rev13, `check41`'s mtime bug), one level up:
a guard whose test suite is drawn from the same assumption as the guard.

## Proposed fix, and its limit stated first

**No lexer-based fix is complete.** `$(cat /tmp/p)`, an alias, a variable read
from a file, or a `python3 -c` that builds the path at runtime all defeat any
static analysis of the command string. The goal is to close the forms a person or
an agent will actually produce, not to claim soundness.

1. **Expand what is safely expandable.** Resolve `${PWD}`/`$PWD` and simple
   `VAR=value` assignments that appear earlier in the same command, then re-test.
   Leaves command substitution unhandled, deliberately.
2. **Track `cd`.** `segments()` already splits on `;`/`&&`/`||`. When a segment is
   `cd <path>`, resolve subsequent relative write targets against it. This closes
   the third case, which is the one most likely to be hit by accident.
3. **Refuse what cannot be decided.** If a write target contains an unexpanded `$`
   after step 1, refuse with that as the stated reason. Fail-closed is the house
   style here (`_input.py`, `decision-guard`), and a false refusal costs a
   rephrase while a false permit costs a silent write into machinery.

## E1 cases owed (`ci/test_hooks.sh` is protected too)

Each of the three permitted forms above → **refused**. Plus the controls, which
matter more than the cases:

- `D=/tmp/scratch; cp x "$D/notes.md"` → **permitted**. Without this, step 3 could
  refuse every command containing a `$` and the suite would still pass.
- `cd docs && cp ../x notes.md` → **permitted**. Same reason for step 2.
- `cd harden/checks && cat check35_controls.py` → **permitted**. Reading about a
  check is not writing one; this is the `check33b` mistake (AUDIT-rev7) waiting to
  be repeated by a `cd`-aware matcher.
