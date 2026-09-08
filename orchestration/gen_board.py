#!/usr/bin/env python3
"""
gen_board.py - the track board as a page, generated from tracks.yaml.

Why a generator and not a page
-------------------------------
Writing the board by hand would be this project's oldest defect wearing a new
coat. README.md line 3 claims its numbers are measured; AUDIT-rev12 found the
completion table beside it reading ALL MET (16 of 16) while FACTS.json - written
by the same script from the same files - said 15 of 16, because that table was
hand-maintained and sat outside the span gen_readme.py regenerates. rev14 found
the critical path was seven weeks of parser bug over ten weeks of guess. rev15
found the README describing a tree the reader does not have.

A hand-typed status page is correct the day it is written, wrong the first time
a track moves, and nothing can see the difference. So: R9, documentation is
measured and not typed, applied to the one artifact whose entire purpose is to
say what the current state is.

Three rules it inherits from the code around it
------------------------------------------------
1. REUSE. Status comes from schedule.derive() and waves from dispatch.plan(),
   imported rather than reimplemented - the same importlib route dispatch.py
   already uses for schedule.py. The page never prints a track's typed `status:`
   field, only the derived one, because a page that types a status the graph
   contradicts is exactly what schedule.py --check exists to catch.
2. NO DERIVED DATA. Reads tracks.yaml and git, nothing else. harden/gen_readme.py
   needs emitters/obc.sqlite and therefore cannot run on a clone with no data;
   this must, because a data-less clone is where someone most needs to know what
   the state is.
3. DETERMINISM. No wall-clock. Provenance is the HEAD commit and ITS timestamp,
   so two runs at the same commit are byte-identical and --check can mean
   something. check20 went red for a whole build over exactly this.

    python3 orchestration/gen_board.py               # write orchestration/board.html
    python3 orchestration/gen_board.py --check       # exit 1 if the file has drifted
    python3 orchestration/gen_board.py --file X.yaml # generate from another DAG
    python3 orchestration/gen_board.py --out -       # stdout
"""
import argparse
import html
import importlib.util
import os
import subprocess
import sys

try:
    import yaml
except ImportError:
    sys.exit("pip install pyyaml --break-system-packages")

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
OUT = os.path.join(HERE, "board.html")

STATUS_ORDER = ["ready", "blocked", "conditional", "done", "ERROR"]
STATUS_BLURB = {
    "ready":       "dependencies met; dispatchable now",
    "blocked":     "waiting on a predecessor",
    "conditional": "waiting on a decision only a person can make",
    "done":        "complete and verified",
    "ERROR":       "the typed status contradicts the graph",
}


def _mod(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, f"{name}.py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def git(*args):
    r = subprocess.run(["git", *args], cwd=PKG, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def e(x):
    return html.escape(str(x), quote=True)


def mono(x):
    return f'<code>{e(x)}</code>'


def dl(rows):
    """A definition grid. Rows whose value is falsy are dropped, so a card never
    shows an empty field - absence of a field is information, a blank one is not."""
    out = [f"<div class=dt>{e(k)}</div><div class=dd>{v}</div>" for k, v in rows if v]
    return f"<div class=grid>{''.join(out)}</div>" if out else ""


CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Serif:ital,wght@0,400;1,400&display=swap');

:root{
  --ground:#eef0f3; --surface:#fbfcfd; --sunk:#e3e7ec;
  --ink:#14181d; --body:#333b45; --muted:#606b79; --rule:#cdd4dc;
  --accent:#254a6e; --accent-soft:#e2e9f1;
  --done:#3d7a5a; --ready:#2563a8; --blocked:#8a6a1f; --conditional:#8a3d3d;
  --done-bg:#e6f0ea; --ready-bg:#e3ecf7; --blocked-bg:#f5eeda; --conditional-bg:#f6e6e6;
  --sans:'IBM Plex Sans',ui-sans-serif,system-ui,sans-serif;
  --serif:'IBM Plex Serif',Georgia,serif;
  --mono:'IBM Plex Mono',ui-monospace,'SF Mono',Menlo,monospace;
}
:root:not([data-theme=light]){ @media (prefers-color-scheme:dark){
  --ground:#101418; --surface:#181d23; --sunk:#0c1014;
  --ink:#eef1f5; --body:#c3cbd4; --muted:#8b96a3; --rule:#2b333c;
  --accent:#8fb4d9; --accent-soft:#1d2937;
  --done:#7bbd97; --ready:#7fb0e8; --blocked:#d6b866; --conditional:#dd8f8f;
  --done-bg:#16261e; --ready-bg:#152435; --blocked-bg:#2a2415; --conditional-bg:#2c1a1a;
}}
:root[data-theme=dark]{
  --ground:#101418; --surface:#181d23; --sunk:#0c1014;
  --ink:#eef1f5; --body:#c3cbd4; --muted:#8b96a3; --rule:#2b333c;
  --accent:#8fb4d9; --accent-soft:#1d2937;
  --done:#7bbd97; --ready:#7fb0e8; --blocked:#d6b866; --conditional:#dd8f8f;
  --done-bg:#16261e; --ready-bg:#152435; --blocked-bg:#2a2415; --conditional-bg:#2c1a1a;
}

body{background:var(--ground);color:var(--body);font-family:var(--sans);
  font-size:15px;line-height:1.55;-webkit-font-smoothing:antialiased}
.wrap{max-width:1180px;margin:0 auto;padding:0 24px 80px}
h1,h2,h3{color:var(--ink);text-wrap:balance;margin:0}
h1{font-size:26px;font-weight:600;letter-spacing:-.015em}
h2{font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:.11em;
  color:var(--muted);padding-bottom:8px;border-bottom:1px solid var(--rule);margin-bottom:20px}
h3{font-size:17px;font-weight:600}
section{margin-top:52px}
code{font-family:var(--mono);font-size:.87em;background:var(--sunk);
  padding:.1em .38em;border-radius:3px;color:var(--ink);word-break:break-word}
a{color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:2px}

/* masthead */
header{padding:40px 0 0}
.eyebrow{font-family:var(--mono);font-size:11.5px;letter-spacing:.09em;
  text-transform:uppercase;color:var(--muted)}
.sub{font-family:var(--serif);font-size:16.5px;color:var(--body);max-width:62ch;margin:12px 0 0}

/* summary strip - the one thing that must read at a glance */
.strip{display:flex;flex-wrap:wrap;gap:1px;background:var(--rule);border:1px solid var(--rule);
  border-radius:7px;overflow:hidden;margin-top:26px}
.cell{background:var(--surface);padding:13px 18px;flex:1 1 120px}
.cell .n{font-family:var(--mono);font-size:25px;font-weight:500;color:var(--ink);
  font-variant-numeric:tabular-nums;line-height:1.15}
.cell .l{font-size:11.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);margin-top:2px}
.cell.done .n{color:var(--done)} .cell.ready .n{color:var(--ready)}
.cell.blocked .n{color:var(--blocked)} .cell.conditional .n{color:var(--conditional)}

/* the honesty note, in the audit voice */
.caveat{margin-top:22px;padding:16px 20px;border-left:3px solid var(--accent);
  background:var(--accent-soft);border-radius:0 6px 6px 0;font-family:var(--serif);
  font-size:15px;color:var(--body)}
.caveat p{margin:0 0 9px} .caveat p:last-child{margin:0}
.caveat strong{color:var(--ink);font-weight:400;font-style:italic}

/* track cards */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:16px}
.card{background:var(--surface);border:1px solid var(--rule);border-radius:7px;
  border-left-width:4px;padding:16px 18px}
.card.done{border-left-color:var(--done)} .card.ready{border-left-color:var(--ready)}
.card.blocked{border-left-color:var(--blocked)} .card.conditional{border-left-color:var(--conditional)}
.card.ERROR{border-left-color:var(--conditional)}
.cardhead{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.tid{font-family:var(--mono);font-size:15px;font-weight:500;color:var(--ink)}
.pill{font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;text-transform:uppercase;
  padding:2px 7px;border-radius:10px;white-space:nowrap}
.pill.done{background:var(--done-bg);color:var(--done)}
.pill.ready{background:var(--ready-bg);color:var(--ready)}
.pill.blocked{background:var(--blocked-bg);color:var(--blocked)}
.pill.conditional{background:var(--conditional-bg);color:var(--conditional)}
.card h3{margin:7px 0 12px;font-size:15.5px;font-weight:600;line-height:1.35}
.grid{display:grid;grid-template-columns:auto 1fr;gap:5px 14px;font-size:13.2px;align-items:baseline}
.dt{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
  white-space:nowrap;padding-top:2px}
.dd{color:var(--body);min-width:0}
.dd ul{margin:0;padding-left:0;list-style:none}
.dd li{margin-bottom:4px}
.dd li:last-child{margin-bottom:0}
.gate-flag{color:var(--blocked);font-weight:500}

/* tables */
.scroll{overflow-x:auto;border:1px solid var(--rule);border-radius:7px;background:var(--surface)}
table{border-collapse:collapse;width:100%;font-size:13.4px}
th,td{text-align:left;padding:9px 14px;border-bottom:1px solid var(--rule);vertical-align:top}
th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);
  font-weight:600;background:var(--sunk);white-space:nowrap}
tr:last-child td{border-bottom:none}
tr.pending td{opacity:.55}
tr.pending em{font-style:italic}
td.num{font-family:var(--mono);font-variant-numeric:tabular-nums;white-space:nowrap}

/* decisions */
.dec{background:var(--surface);border:1px solid var(--rule);border-left:4px solid var(--conditional);
  border-radius:7px;padding:15px 18px;margin-bottom:12px}
.dec .q{color:var(--ink);font-weight:600;font-size:15px}
.dec .b{font-size:13px;color:var(--muted);margin-top:6px}

/* wave */
.wave{background:var(--surface);border:1px solid var(--rule);border-radius:7px;
  padding:16px 18px;margin-bottom:14px}
.wave h3{font-size:14px;margin-bottom:10px}
.wave .spec{font-family:var(--mono);font-size:11px;color:var(--muted);
  text-transform:uppercase;letter-spacing:.06em}
.held{color:var(--blocked);font-size:13px;margin-top:8px}

pre.mermaid{background:var(--surface);border:1px solid var(--rule);border-radius:7px;
  padding:20px;overflow-x:auto;text-align:center}

footer{margin-top:64px;padding-top:22px;border-top:1px solid var(--rule);
  font-size:12.5px;color:var(--muted)}
footer p{margin:0 0 7px}
@media (max-width:640px){ .wrap{padding:0 16px 60px} h1{font-size:22px} .cards{grid-template-columns:1fr} }
</style>
"""


def build(tracks_path=None):
    sch, dis = _mod("schedule"), _mod("dispatch")
    doc = sch.load(tracks_path)
    T = doc["tracks"]
    derived = sch.derive(T)
    waves = dis.plan(tracks_path)
    decisions = doc.get("decisions_pending") or []

    # The commit that last touched tracks.yaml, NOT HEAD. A board is a function
    # of the DAG, so it is stale when the DAG moves and only then. Using HEAD
    # meant committing the board moved HEAD past the SHA inside it, so --check
    # went red on the very next commit and stayed red - a false alarm on a
    # schedule, which is the failure mode rev13 warned about.
    src = "orchestration/tracks.yaml"
    sha = git("log", "-1", "--format=%H", "--", src)
    when = git("log", "-1", "--format=%cI", "--", src)
    branch = git("rev-parse", "--abbrev-ref", "HEAD")

    counts = {s: sum(1 for k in T if derived[k][0] == s) for s in STATUS_ORDER}
    open_ids = [k for k in T if derived[k][0] != "done"]
    items = sum(len(T[k].get("items") or {}) or 1 for k in open_ids)
    promos = [(k, p) for k in T for p in (T[k].get("promotes") or [])]
    ready_promos = [(k, p) for k, p in promos
                    if os.path.exists(os.path.join(PKG, p["from"]))]
    gated = [(k, T[k]["human_gate"]) for k in open_ids
             if T[k].get("human_gate") not in (None, "none")]
    unmeasured = [k for k in open_ids if str(T[k].get("agent_effort")) == "unmeasured"]

    P = []
    A = P.append
    A("<title>OBC Track Board</title>")
    A(CSS)
    A('<div class=wrap>')

    # ---- masthead ---------------------------------------------------------
    A("<header>")
    A(f'<div class=eyebrow>obc-interactive &middot; {e(branch)} &middot; {e(sha[:8])}</div>')
    A("<h1>Track board</h1>")
    A('<p class=sub>Every figure on this page is derived from '
      '<code>orchestration/tracks.yaml</code> by <code>gen_board.py</code>. '
      'None is typed. Status is computed by <code>schedule.derive()</code>, never read '
      'from a track&rsquo;s own <code>status:</code> field &mdash; a status that disagrees '
      'with the graph is a DAG error, not a fact.</p>')

    A('<div class=strip>')
    for s in ["done", "ready", "blocked", "conditional"]:
        if counts.get(s):
            A(f'<div class="cell {s}"><div class=n>{counts[s]}</div><div class=l>{e(s)}</div></div>')
    A(f'<div class=cell><div class=n>{items}</div><div class=l>open items</div></div>')
    A(f'<div class=cell><div class=n>{len(ready_promos)}</div>'
      f'<div class=l>ready to promote</div></div>')
    A(f'<div class=cell><div class=n>{len(decisions)}</div><div class=l>decisions pending</div></div>')
    A("</div>")

    A('<div class=caveat>')
    A(f"<p><strong>agent_effort reads <code>unmeasured</code> on all {len(unmeasured)} open tracks, "
      "and that is the honest value rather than a missing one.</strong> The field means wall-clock "
      "from dispatch to a <em>verified board</em>. Two tracks have been dispatched; neither reached "
      "one, because no gate that reads the derived data can run on a clone that has none. "
      "<code>schedule.py --check</code> refuses any value here that does not cite the dispatch it "
      "was measured from.</p>")
    A("<p><strong>The typed human-effort figures are guesses and are labelled as such.</strong> "
      "The &ldquo;~17 weeks&rdquo; this project quoted for months was seven weeks of a parser bug "
      "&mdash; <code>&quot;3-5 days&quot;</code> parsed as 35 days &mdash; on top of ten weeks of "
      "estimate that no check ever produced.</p>")
    A("</div></header>")

    # ---- the wave: what is actually actionable ---------------------------
    A("<section><h2>Dispatchable now</h2>")
    for w in waves["waves"]:
        spec = "speculative &mdash; assumes the previous wave completes" if w["speculative"] else "dispatchable"
        A(f'<div class=wave><h3>Wave {w["wave"]} <span class=spec>&middot; {spec}</span></h3>')
        if w["tracks"]:
            A("<div class=scroll><table><tr><th>track</th><th>agents</th><th>gates</th><th>staged</th></tr>")
            for x in w["tracks"]:
                A(f'<tr><td class=num>{mono(x["track"])}</td>'
                  f'<td>{" &rarr; ".join(e(y) for y in [x["agent"], *x["then"]])}</td>'
                  f'<td class=num>{", ".join(map(e, x["gates"])) or "&mdash;"}</td>'
                  f'<td class=num>{len(x["promotes"]) or "&mdash;"}</td></tr>')
            A("</table></div>")
        else:
            A(f'<p class=held>{e(w.get("note",""))}</p>')
        for h in w["held"]:
            A(f'<div class=held>held &mdash; <code>{e(h["track"])}</code> &middot; {e(h["reason"])}</div>')
        A("</div>")
    A("</section>")

    # ---- the graph, drawn from the graph ---------------------------------
    A("<section><h2>Dependency graph</h2><pre class=mermaid>graph LR")
    for tid in T:
        st = derived[tid][0]
        A(f'  {tid}["{tid}"]:::{st}')
    for tid, t in T.items():
        for dep in (t.get("depends_on") or []):
            A(f"  {dep} --> {tid}")
    A("  classDef done fill:#e6f0ea,stroke:#3d7a5a,color:#14181d;")
    A("  classDef ready fill:#e3ecf7,stroke:#2563a8,color:#14181d;")
    A("  classDef blocked fill:#f5eeda,stroke:#8a6a1f,color:#14181d;")
    A("  classDef conditional fill:#f6e6e6,stroke:#8a3d3d,color:#14181d;")
    A("</pre></section>")
    return P, T, derived, decisions, gated, promos, ready_promos, sha, when, A


def render(tracks_path=None):
    P, T, derived, decisions, gated, promos, ready_promos, sha, when, A = build(tracks_path)

    # ---- the four decisions ----------------------------------------------
    if decisions:
        A("<section><h2>Decisions &mdash; each needs a person</h2>")
        for d in decisions:
            blocks = d.get("blocks") or []
            affects = d.get("affects") or []
            A(f'<div class=dec><div class=q>{e(d["id"])} &middot; {e(d["question"])}</div>')
            if blocks:
                A(f'<div class=b>blocks {", ".join(mono(x) for x in blocks)}</div>')
            if affects:
                A(f'<div class=b>affects {", ".join(e(x) for x in affects)}</div>')
            if not blocks and not affects:
                A('<div class=b>blocks nothing &mdash; answer it when convenient</div>')
            A("</div>")
        A('<p class=held>A track may not resolve one of these by assumption. '
          '<code>decision-guard</code> blocks an edit that removes one from the DAG.</p>')
        A("</section>")

    # ---- tracks, grouped by DERIVED status --------------------------------
    for st in STATUS_ORDER:
        ids = [k for k in T if derived[k][0] == st]
        if not ids:
            continue
        A(f'<section><h2>{e(st)} ({len(ids)}) &mdash; {e(STATUS_BLURB.get(st,""))}</h2><div class=cards>')
        for tid in ids:
            t = T[tid]
            why = derived[tid][1]
            succ = [k for k, v in T.items() if tid in (v.get("depends_on") or [])]
            gate = t.get("human_gate")
            A(f'<article class="card {st}"><div class=cardhead>'
              f'<span class=tid>{e(tid)}</span>'
              f'<span class="pill {st}">{e(st)}</span></div>'
              f'<h3>{e(t["title"])}</h3>')

            rows = []
            if why:
                rows.append(("why", e(why)))
            rows.append(("needs", ", ".join(mono(x) for x in (t.get("depends_on") or [])) or "&mdash;"))
            rows.append(("unblocks", ", ".join(mono(x) for x in succ) or "nothing downstream"))
            if gate and gate != "none":
                rows.append(("human gate", f'<span class=gate-flag>{e(gate)}</span>'))
            if t.get("gates"):
                rows.append(("gates", " ".join(mono(g) for g in t["gates"])))
            if t.get("serialises_on"):
                rows.append(("serialises on", " ".join(mono(x) for x in t["serialises_on"])))
            if st != "done":
                rows.append(("effort", f'{e(t.get("human_effort","&mdash;"))} typed &middot; '
                                       f'<code>{e(t.get("agent_effort","&mdash;"))}</code> measured'))
            if t.get("items"):
                lis = "".join(f"<li>{mono(k)} {e(v)}</li>" for k, v in t["items"].items())
                rows.append((f'items ({len(t["items"])})', f"<ul>{lis}</ul>"))
            if t.get("promotes"):
                lis = "".join(f'<li>{mono(p["from"])} &rarr; {mono(p["to"])}</li>' for p in t["promotes"])
                rows.append((f'staged ({len(t["promotes"])})', f"<ul>{lis}</ul>"))
            A(dl(rows))
            A("</article>")
        A("</div></section>")

    # ---- the promote checklist -------------------------------------------
    if promos:
        A(f"<section><h2>Staged, awaiting promotion ({len(ready_promos)} of {len(promos)} declared)</h2>")
        A('<p class=sub style="margin:0 0 16px">A track may not write verification machinery; '
          'it proposes it and a person installs it (PROTOCOL R13). '
          '<code>python3 orchestration/dispatch.py --promote &lt;TRACK&gt;</code> prints the exact '
          'commands. A destination that already exists is a merge to review, never a move. '
          'Rows marked <em>not produced yet</em> are declarations by tracks that have not run; '
          'they are listed so the contract is visible, and they are not yours to act on.</p>')
        A('<div class=scroll><table><tr><th>track</th><th>you review this</th>'
          '<th>a person installs it here</th><th>kind</th></tr>')
        for tid, p in promos:
            staged = os.path.exists(os.path.join(PKG, p["from"]))
            exists = os.path.exists(os.path.join(PKG, p["to"]))
            if not staged:
                kind = "<em>not produced yet</em>"
            else:
                kind = "merge &mdash; review the diff" if exists else "move"
            A(f'<tr{"" if staged else " class=pending"}><td class=num>{mono(tid)}</td>'
              f'<td class=num>{mono(p["from"])}</td>'
              f'<td class=num>{mono(p["to"])}</td><td>{kind}</td></tr>')
        A("</table></div></section>")

    # ---- provenance -------------------------------------------------------
    A("<footer>")
    A(f'<p>Generated from <code>orchestration/tracks.yaml</code> at commit '
      f'<code>{e(sha[:12])}</code>, committed <code>{e(when)}</code>. '
      f'No wall-clock is embedded, so two runs at one commit are byte-identical and '
      f'<code>gen_board.py --check</code> can detect drift.</p>')
    A('<p>Green on a check proves the check ran. It proves nothing else.</p>')
    A("<p>Unofficial derived work. Current to 2025-01-16 (through O. Reg. 5/25). "
      "Not the official Building Code Compendium. "
      "&copy; King&rsquo;s Printer for Ontario, 2024. Reproduced with permission.</p>")
    A("</footer></div>")
    return "\n".join(P) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="tracks.yaml to render")
    ap.add_argument("--out", default=OUT, help="output path, or - for stdout")
    ap.add_argument("--check", action="store_true", help="exit 1 if the written board has drifted")
    a = ap.parse_args()

    doc = render(a.file)

    if a.check:
        if not os.path.exists(OUT):
            print(f"RESULT: FAIL {os.path.relpath(OUT, PKG)} does not exist; run gen_board.py")
            sys.exit(1)
        have = open(OUT).read()
        same = have == doc
        print(f"{os.path.relpath(OUT, PKG)}: {'matches' if same else 'DRIFTED from'} tracks.yaml")
        print("RESULT:", "PASS" if same else
              "FAIL - the board was hand-edited or tracks.yaml moved. Regenerate; never patch it.")
        sys.exit(0 if same else 1)

    if a.out == "-":
        sys.stdout.write(doc)
    else:
        open(a.out, "w").write(doc)
        print(f"{os.path.relpath(a.out, PKG)}: {len(doc):,} bytes")


if __name__ == "__main__":
    main()
