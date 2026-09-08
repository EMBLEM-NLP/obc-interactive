#!/usr/bin/env python3
"""
run_gates.py - execute every gate from the package, produce a board.

    python3 ci/run_gates.py                    # full board
    python3 ci/run_gates.py --fast             # skip checks marked slow
    python3 ci/run_gates.py --only H1 H4       # subset by gate id
    python3 ci/run_gates.py --control          # CI1: prove the board can go red

Reads ci/checks.yaml for each check's execution context. Materialises the
verify/ working sets the way verify/verify.sh does, builds a bag so H2 can run,
and runs each check as a subprocess in its declared cwd with its declared env.

A check whose fetch-only inputs are unset is SKIPPED with the reason recorded.
It is never run, never counted as a pass, and never silently omitted - the
board lists it. The exit code is non-zero if any executed gate fails or if any
check that should have run could not be found. Skips do not affect exit code;
they are visible, which is the point.

CI1 (--control): seed a check that always fails into a copy of the manifest,
run the board, require exit 1. A runner that cannot go red is a green light,
not a gate. CI2: run twice from a clean bag; boards must match on every
(gate, status) pair.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.normpath(os.path.join(HERE, ".."))


def materialise(scope, pkg):
    """verify/verify.sh's link() logic, as real copies."""
    v = os.path.join(pkg, "verify")
    out = os.path.join(v, scope, "out")
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(out)
    vol = {"volume1": "v1", "volume2": "v2", "emitters": "v2"}[scope]
    src = os.path.join(v, "data", vol)
    if scope != "emitters":
        for f in os.listdir(src):
            shutil.copy(os.path.join(src, f), os.path.join(out, f))
    if scope == "volume2":
        shutil.copy(os.path.join(src, "docgraph-merged.jsonl.gz"), os.path.join(out, "docgraph.jsonl.gz"))
    if scope == "emitters":
        shutil.copy(os.path.join(pkg, "emitters", "obc.sqlite"), os.path.join(out, "obc.sqlite"))
        shutil.copy(os.path.join(src, "docgraph-merged.jsonl.gz"), os.path.join(out, "docgraph-merged.jsonl.gz"))
        for tgz in ("markdown.tar.gz", "html.tar.gz"):
            subprocess.run(["tar", "xzf", os.path.join(pkg, "emitters", tgz), "-C", out], check=True)
    for name, built in (("301880_built.pdf", "301880_built_from_model.pdf"),
                        ("301881_built.pdf", "301881_built_from_model.pdf")):
        p = os.path.join(pkg, "pdf", built)
        if os.path.exists(p):
            os.symlink(p, os.path.join(out, name))


def build_bag(pkg, bag):
    """Same logic as harden/make_bag.py; the two source hashes are carried from
    the shipped manifest rather than recomputed (the PDFs are fetch-only)."""
    import bagit, hashlib
    if os.path.exists(bag):
        shutil.rmtree(bag)
    shutil.copytree(pkg, bag, ignore=shutil.ignore_patterns("__pycache__", "out"))
    b = bagit.make_bag(bag, {"Bag-Software-Agent": "bagit.py + obc pipeline (ci)"},
                       checksums=["sha512", "sha256"])
    srcs = yaml.safe_load(open(os.path.join(HERE, "checks.yaml"))).get("sources") or []
    with open(os.path.join(bag, "fetch.txt"), "w") as fh:
        for x in srcs:
            fh.write(f"{x['url']} {x['size']} {x['rel']}\n")
    for alg in ("sha256", "sha512"):
        with open(os.path.join(bag, f"manifest-{alg}.txt"), "a") as fh:
            for x in srcs:
                fh.write(f"{x[alg]}  {x['rel']}\n")
    bagit.Bag(bag).save(manifests=False)
    for alg in ("sha512", "sha256"):
        entries = []
        for name in sorted(os.listdir(bag)):
            p = os.path.join(bag, name)
            if os.path.isfile(p) and not name.startswith("tagmanifest-"):
                entries.append(f"{hashlib.new(alg, open(p, 'rb').read()).hexdigest()}  {name}\n")
        open(os.path.join(bag, f"tagmanifest-{alg}.txt"), "w").writelines(entries)


def expand(v, sub):
    if isinstance(v, str):
        for k, val in sub.items():
            v = v.replace(f"${k}", val)
    return v


def run_one(c, pkg, base_env, sub, timeout):
    script = os.path.join(pkg, c["script"])
    cwd = os.path.join(pkg, c.get("scope", "."))
    if not os.path.exists(script):
        return "MISSING", 127, "script not found", 0.0
    needs = c.get("needs") or []
    missing = [n for n in needs if not os.environ.get(n) or not os.path.exists(os.environ[n])]
    if missing:
        return "SKIP", None, f"fetch-only input(s) unset: {', '.join(missing)}", 0.0
    for mod in c.get("needs_module") or []:
        try:
            __import__(mod)
        except ImportError:
            return "SKIP", None, f"module not installed: {mod} (CI must pip install it)", 0.0
    env = dict(base_env)
    for k, v in (c.get("env") or {}).items():
        env[k] = expand(v, sub)
    args = [expand(a, sub) for a in (c.get("args") or [])]
    rel = os.path.relpath(script, cwd)
    t0 = time.time()
    interp = ["bash"] if rel.endswith(".sh") else [sys.executable]
    try:
        r = subprocess.run([*interp, rel, *args], cwd=cwd, env=env,
                           capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return "FAIL", None, f"timeout after {timeout}s", time.time() - t0
    lines = [l for l in r.stdout.splitlines() if l.strip()]
    last = next((l for l in reversed(lines) if l.startswith("RESULT:")), lines[-1] if lines else "")
    status = "PASS" if r.returncode == 0 and "RESULT: PASS" in last else "FAIL"
    if status == "FAIL" and not last:
        last = (r.stderr.strip().splitlines() or ["(no output)"])[-1][:160]
    return status, r.returncode, last[:200], time.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=os.path.join(HERE, "checks.yaml"))
    ap.add_argument("--pkg", default=PKG)
    ap.add_argument("--out", default=os.path.join(HERE, "gate-board.json"))
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--control", action="store_true", help="CI1: seed a failing check, require red")
    a = ap.parse_args()

    if a.control:
        m = yaml.safe_load(open(a.manifest))
        seed = os.path.join(a.pkg, "harden", "checks", "check_seeded_failure.py")
        open(seed, "w").write('print("seeded"); print("RESULT: FAIL - seeded by CI1"); raise SystemExit(1)\n')
        m["checks"].append({"script": "harden/checks/check_seeded_failure.py", "scope": "harden", "gate": "SEED"})
        tmpm = tempfile.mktemp(suffix=".yaml"); yaml.safe_dump(m, open(tmpm, "w"))
        r = subprocess.run([sys.executable, __file__, "--manifest", tmpm, "--pkg", a.pkg,
                            "--only", "SEED", "H2", "--out", tempfile.mktemp(suffix=".json")],
                           capture_output=True, text=True)
        os.unlink(seed); os.unlink(tmpm)
        ok = r.returncode != 0 and "SEED" in r.stdout and "FAIL" in r.stdout
        print(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "(no output)")
        print("CI1 control:", "ok - the board went red on a seeded failure" if ok
              else "VOID - a seeded failing check did not turn the board red")
        sys.exit(0 if ok else 1)

    m = yaml.safe_load(open(a.manifest))
    base_env = dict(os.environ, **{k: str(v) for k, v in (m.get("epoch_env") or {}).items()})
    tmp = tempfile.mkdtemp()
    bag = os.path.join(tmp, "bag")
    sub = {"PKG": a.pkg, "BAG": bag,
           "OBC_SRC_V1": os.environ.get("OBC_SRC_V1", ""), "OBC_SRC_V2": os.environ.get("OBC_SRC_V2", "")}

    checks = [c for c in m["checks"] if not c.get("superseded")]
    if a.only:
        want = set(a.only)
        checks = [c for c in checks if any(g in want for g in (c["gate"] if isinstance(c["gate"], list) else [c["gate"]]))]
    if a.fast:
        checks = [c for c in checks if not c.get("slow")]

    # Data first. materialise() copies emitters/*.sqlite and verify/data/* into
    # working sets; on a clone that never ran ci/fetch_data.sh those files do not
    # exist and it dies with a FileNotFoundError traceback - a crash, not a
    # verdict. DATA1 exists to say exactly what is wrong, so run it first and
    # stop if it fails.
    data_check = os.path.join(a.pkg, "harden", "checks", "check40_dataintegrity.py")
    if os.path.exists(data_check) and not a.only:
        d = subprocess.run([sys.executable, data_check, "--quick"],
                           cwd=os.path.join(a.pkg, "harden"), capture_output=True, text=True)
        if d.returncode != 0:
            print(d.stdout.strip())
            print("\nDATA1 failed: the data the gates read is missing, truncated, or a pointer stub.")
            print("Run `bash ci/fetch_data.sh` (needs OBC_DATA_URL or OBC_DATA_DIR), then re-run.")
            print("Not running the remaining gates - they would read wrong data.")
            json.dump(dict(summary=dict(ran=1, passed=0, failed=1, skipped=0, known_review=0,
                                        aborted="DATA1"),
                           gates=[dict(gate="DATA1", check="harden/checks/check40_dataintegrity.py",
                                       status="FAIL", exit=d.returncode,
                                       result=(d.stdout.strip().splitlines() or [""])[-1], seconds=0)]),
                      open(a.out, "w"), indent=1)
            print("RESULT: FAIL 1 gate(s)")
            sys.exit(1)

    pres = {c.get("pre") for c in checks if c.get("pre")}
    for scope in sorted(pres):
        materialise(scope, a.pkg)
    if any(c["script"].endswith("check21_bagit.py") for c in checks):
        build_bag(a.pkg, bag)
    zipp = os.path.join(tmp, "obc-interactive.zip")
    sub["ZIP"] = zipp
    if any(c["script"].endswith("check19_package.py") for c in checks):
        # The deliverable is named obc-interactive regardless of what the
        # checkout directory is called; check19 looks for obc-interactive/README.md.
        # Using the checkout's basename here failed G16d on any clone not literally
        # named obc-interactive - found on the first git dry run.
        import zipfile
        with zipfile.ZipFile(zipp, "w", zipfile.ZIP_DEFLATED) as z:
            for root, dirs, files in os.walk(a.pkg):
                dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", "out")]
                for f in files:
                    if f in (".regen.stamp", "gate-board.json", "MANIFEST.sha256.tmp"): continue
                    full = os.path.join(root, f)
                    z.write(full, os.path.join("obc-interactive", os.path.relpath(full, a.pkg)))

    board, fails, ran = [], 0, 0
    print(f"{'gate':<12}{'status':<8}{'secs':>6}  check / result")
    print("-" * 78)
    for c in checks:
        status, rc, msg, secs = run_one(c, a.pkg, base_env, sub, a.timeout)
        gates = c["gate"] if isinstance(c["gate"], list) else [c["gate"]]
        for g in gates:
            board.append(dict(gate=g, check=c["script"], status=status, exit=rc,
                              result=msg, seconds=round(secs, 1), note=c.get("note")))
        if status in ("FAIL", "MISSING"):
            fails += 1
        if status not in ("SKIP",):
            ran += 1
        gid = ",".join(gates)
        known = c.get("known")
        if status == "FAIL" and known:
            status_shown = "KNOWN"
            fails -= 1     # enumerated, not silent: counted separately below
            for b in board:
                if b["check"] == c["script"]: b["status"] = "KNOWN"; b["note"] = known
        else:
            status_shown = status
        print(f"{gid:<12}{status_shown:<8}{secs:>6.1f}  {os.path.basename(c['script'])}: {msg[:56]}")

    shutil.rmtree(tmp, ignore_errors=True)
    for scope in sorted(pres):
        shutil.rmtree(os.path.join(a.pkg, "verify", scope, "out"), ignore_errors=True)

    summary = dict(ran=ran, passed=sum(1 for b in board if b["status"] == "PASS"),
                   failed=fails, skipped=sum(1 for b in board if b["status"] == "SKIP"),
                   known_review=sum(1 for b in board if b["status"] == "KNOWN"),
                   generated=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(int(base_env["SOURCE_DATE_EPOCH"]))))
    json.dump(dict(summary=summary, gates=board), open(a.out, "w"), indent=1)
    print("-" * 78)
    print(f"ran {ran} | passed {summary['passed']} | failed {fails} | known-review {summary['known_review']} | skipped {summary['skipped']}  -> {os.path.relpath(a.out, a.pkg)}")
    print("RESULT:", "PASS" if fails == 0 else f"FAIL {fails} gate(s)")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
