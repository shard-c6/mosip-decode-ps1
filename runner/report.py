"""
The consolidated, human-readable conformance report.

The contract JSON is for machines -- the api-testrig classes and CI read it. This renders
the same document for people: one page covering every component in the run, what the
suite said about each module, what the benchmark gate decided and why, plus a status badge.
It is what the problem statement's combined mode calls "one consolidated cross-module
conformance report and badge".

Rendering only: nothing here talks to the network or changes a verdict. Any result file
can be re-rendered later:

    python -m runner.report results/conformance.json --out results/report
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path
from typing import Any

# The suite's own result vocabulary, in the order the report counts it.
RESULTS = ["PASSED", "REVIEW", "WARNING", "SKIPPED", "FAILED"]

_COMPONENT_TITLES = {
    "inji-verify": "Inji Verify",
    "inji-certify": "Inji Certify",
}


def write(document: dict[str, Any], out_dir: Path) -> list[Path]:
    """Write report.md, report.html and badge.svg into `out_dir`; return the paths."""
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "report.md": markdown(document),
        "report.html": html_page(document),
        "badge.svg": badge(document),
    }
    paths = []
    for name, text in files.items():
        path = out_dir / name
        path.write_text(text)
        paths.append(path)
    return paths


# --- the facts the three renderings share ----------------------------------------------


def _title(component: dict[str, Any]) -> str:
    name = component.get("component", "unknown")
    return _COMPONENT_TITLES.get(name, name)


def _counts(component: dict[str, Any]) -> dict[str, int]:
    counts = {r: 0 for r in RESULTS}
    for module in component.get("modules", []):
        result = module.get("result") or "UNKNOWN"
        counts[result] = counts.get(result, 0) + 1
    return counts


def _gate_problems(gate: dict[str, Any]) -> list[str]:
    """Each reason the gate failed, as a sentence."""
    labels = [
        ("regressions", "regressed against the baseline"),
        ("harnessErrors", "could not be run by the harness"),
        ("reviewMismatches", "verifier's verdict contradicts what the test required"),
    ]
    problems = []
    for key, label in labels:
        for entry in gate.get(key, []):
            problems.append(f"{entry.get('component')} / {entry.get('moduleName')}: {label}")
    return problems


def _why(module: dict[str, Any]) -> str:
    """One line explaining the module's verdict: the baseline's reason, or the first failure."""
    if module.get("regression"):
        return f"Regression: expected {module.get('expected')}, got {module.get('result')}"
    if module.get("expectedReason"):
        return str(module["expectedReason"])
    for check in module.get("checks", []):
        if check.get("result") == "FAILURE":
            return f"[{check.get('src')}] {check.get('msg')}"
    return ""


def _status_line(document: dict[str, Any]) -> tuple[str, str]:
    """('passing' | 'failing', the badge's right-hand text)."""
    gate = document.get("gate", {})
    total = sum(len(c.get("modules", [])) for c in document.get("components", []))
    if gate.get("passed"):
        return "passing", f"gate passing · {total} modules"
    return "failing", f"gate failing · {len(_gate_problems(gate))} problem(s)"


def _badge_label(document: dict[str, Any]) -> str:
    names = [_title(c) for c in document.get("components", [])]
    if len(names) > 1:
        return "Certify ↔ Verify OpenID 1.0" if set(names) == {"Inji Certify", "Inji Verify"} else "OpenID 1.0"
    return f"{names[0]} OpenID 1.0" if names else "OpenID 1.0"


# --- Markdown ---------------------------------------------------------------------------


def markdown(document: dict[str, Any]) -> str:
    run = document.get("run", {})
    gate = document.get("gate", {})
    state, _ = _status_line(document)
    lines = [
        "# OpenID conformance report",
        "",
        f"Run `{run.get('runId', '?')}` · mode **{run.get('mode', '?')}** · "
        f"{run.get('startedAt', '?')} · {round((run.get('durationMs') or 0) / 1000)} s",
        "",
        f"**Gate: {state.upper()}** (policy `{gate.get('policy', '?')}`, baseline updated "
        f"{gate.get('baselineUpdatedAt', '?')})",
        "",
    ]
    problems = _gate_problems(gate)
    if problems:
        lines += ["Why the gate failed:", ""] + [f"- {p}" for p in problems] + [""]
    for key, label in [("improvements", "Now better than the baseline"), ("unknownModules", "No baseline yet")]:
        entries = gate.get(key, [])
        if entries:
            lines += [f"{label}: " + ", ".join(f"{e.get('component')} / {e.get('moduleName')}" for e in entries), ""]

    lines += ["## Summary", "", "| Component | Role | Plan | " + " | ".join(RESULTS) + " | Gate |",
              "|---|---|---|" + "---:|" * len(RESULTS) + "---|"]
    for component in document.get("components", []):
        counts = _counts(component)
        verdicts = [m.get("verdict") for m in component.get("modules", [])]
        ok = "FAIL" not in verdicts
        lines.append(
            f"| {_title(component)} | {component.get('role', '')} | "
            f"[{component.get('plan', {}).get('planName', '')}]({component.get('plan', {}).get('planUrl', '')}) | "
            + " | ".join(str(counts.get(r, 0)) for r in RESULTS)
            + f" | {'pass' if ok else '**fail**'} |"
        )
    lines.append("")

    for component in document.get("components", []):
        plan = component.get("plan", {})
        lines += [
            f"## {_title(component)} — {plan.get('planName', '')}",
            "",
            f"Version {component.get('version', '?')} · endpoint `{component.get('endpoint', '?')}` · "
            f"plan `{plan.get('planId', '?')}`",
            "",
            "| Module | Suite result | Baseline | Gate | Why |",
            "|---|---|---|---|---|",
        ]
        for module in component.get("modules", []):
            why = _why(module).replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| [{module.get('moduleName')}]({module.get('logUrl', '')}) | {module.get('result')} | "
                f"{module.get('expected') or '—'} | {module.get('verdict') or '—'} | {why} |"
            )
        lines.append("")

    lines += [
        "The suite's own result is shown unchanged. The gate compares it with the recorded "
        "baseline (`configs/contract/expected-failures.json`): a known, documented failure "
        "passes the gate; anything worse than its baseline fails it.",
        "",
    ]
    return "\n".join(lines)


# --- HTML -------------------------------------------------------------------------------

_CSS = """
:root { --fg:#1d2330; --muted:#5b6475; --line:#d9dee7; --bg:#ffffff; --head:#f3f5f9;
        --pass:#1a7f37; --fail:#c62828; --warn:#9a6700; --skip:#57606a; }
@media (prefers-color-scheme: dark) {
  :root { --fg:#e6e9ef; --muted:#9aa3b2; --line:#30363d; --bg:#0f1218; --head:#171b22;
          --pass:#3fb950; --fail:#f85149; --warn:#d29922; --skip:#8b949e; } }
body { font: 14px/1.5 system-ui, -apple-system, Segoe UI, sans-serif; color:var(--fg);
       background:var(--bg); margin:0 auto; max-width:1100px; padding:24px 16px; }
h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:17px; margin:28px 0 6px; }
.meta { color:var(--muted); } .gate { font-size:16px; font-weight:600; margin:14px 0; }
table { border-collapse:collapse; width:100%; margin:8px 0; }
th, td { border-bottom:1px solid var(--line); padding:6px 8px; text-align:left; vertical-align:top; }
th { background:var(--head); font-weight:600; } td.n { text-align:right; }
.PASSED,.PASS,.passing { color:var(--pass); font-weight:600; }
.FAILED,.FAIL,.failing { color:var(--fail); font-weight:600; }
.WARNING,.REVIEW { color:var(--warn); font-weight:600; } .SKIPPED,.SKIP { color:var(--skip); }
.why { color:var(--muted); font-size:13px; } .wrap { overflow-x:auto; }
a { color:inherit; }
"""


def html_page(document: dict[str, Any]) -> str:
    e = html.escape
    run = document.get("run", {})
    gate = document.get("gate", {})
    state, _ = _status_line(document)
    parts = [
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'>",
        f"<title>OpenID conformance report</title><style>{_CSS}</style></head><body>",
        f"<h1>OpenID conformance report</h1>{badge(document)}",
        f"<div class='meta'>Run {e(str(run.get('runId', '?')))} · mode {e(str(run.get('mode', '?')))} · "
        f"{e(str(run.get('startedAt', '?')))} · {round((run.get('durationMs') or 0) / 1000)} s</div>",
        f"<div class='gate'>Gate: <span class='{state}'>{state.upper()}</span> "
        f"<span class='meta'>(policy {e(str(gate.get('policy', '?')))})</span></div>",
    ]
    problems = _gate_problems(gate)
    if problems:
        parts.append("<ul>" + "".join(f"<li class='FAIL'>{e(p)}</li>" for p in problems) + "</ul>")

    parts.append("<div class='wrap'><table><tr><th>Component</th><th>Role</th><th>Plan</th>"
                 + "".join(f"<th>{r}</th>" for r in RESULTS) + "<th>Gate</th></tr>")
    for component in document.get("components", []):
        counts = _counts(component)
        ok = "FAIL" not in [m.get("verdict") for m in component.get("modules", [])]
        plan = component.get("plan", {})
        parts.append(
            f"<tr><td>{e(_title(component))}</td><td>{e(str(component.get('role', '')))}</td>"
            f"<td><a href='{e(str(plan.get('planUrl', '')))}'>{e(str(plan.get('planName', '')))}</a></td>"
            + "".join(f"<td class='n'>{counts.get(r, 0)}</td>" for r in RESULTS)
            + f"<td class='{'PASS' if ok else 'FAIL'}'>{'pass' if ok else 'fail'}</td></tr>"
        )
    parts.append("</table></div>")

    for component in document.get("components", []):
        plan = component.get("plan", {})
        parts.append(
            f"<h2>{e(_title(component))} — {e(str(plan.get('planName', '')))}</h2>"
            f"<div class='meta'>Version {e(str(component.get('version', '?')))} · endpoint "
            f"{e(str(component.get('endpoint', '?')))} · plan {e(str(plan.get('planId', '?')))}</div>"
            "<div class='wrap'><table><tr><th>Module</th><th>Suite result</th><th>Baseline</th>"
            "<th>Gate</th><th>Why</th></tr>"
        )
        for module in component.get("modules", []):
            result = str(module.get("result"))
            verdict = str(module.get("verdict") or "—")
            parts.append(
                f"<tr><td><a href='{e(str(module.get('logUrl', '')))}'>{e(str(module.get('moduleName')))}</a></td>"
                f"<td class='{e(result)}'>{e(result)}</td><td>{e(str(module.get('expected') or '—'))}</td>"
                f"<td class='{e(verdict)}'>{e(verdict)}</td><td class='why'>{e(_why(module))}</td></tr>"
            )
        parts.append("</table></div>")

    parts.append(
        "<p class='meta'>The suite's own result is shown unchanged. The gate compares it with the "
        "recorded baseline: a known, documented failure passes the gate; anything worse than its "
        "baseline fails it.</p></body></html>"
    )
    return "".join(parts) + "\n"


# --- badge ------------------------------------------------------------------------------


def badge(document: dict[str, Any]) -> str:
    """A shields-style SVG badge: '<components> OpenID 1.0 | gate passing · N modules'."""
    state, right = _status_line(document)
    left = _badge_label(document)
    colour = "#2e7d32" if state == "passing" else "#c62828"
    # Width estimate for Verdana 11px; close enough for a badge.
    lw, rw = 10 + int(len(left) * 6.6), 10 + int(len(right) * 6.6)
    e = html.escape
    return (
        f"<svg xmlns='http://www.w3.org/2000/svg' width='{lw + rw}' height='20' role='img' "
        f"aria-label='{e(left)}: {e(right)}'><title>{e(left)}: {e(right)}</title>"
        f"<rect width='{lw}' height='20' fill='#555'/><rect x='{lw}' width='{rw}' height='20' fill='{colour}'/>"
        "<g fill='#fff' font-family='Verdana,DejaVu Sans,sans-serif' font-size='11'>"
        f"<text x='{lw / 2}' y='14' text-anchor='middle'>{e(left)}</text>"
        f"<text x='{lw + rw / 2}' y='14' text-anchor='middle'>{e(right)}</text></g></svg>"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m runner.report", description=__doc__.split("\n\n")[0])
    parser.add_argument("result", type=Path, help="a result document written by the runner")
    parser.add_argument("--out", type=Path, required=True, help="directory for report.md, report.html, badge.svg")
    args = parser.parse_args(argv)
    for path in write(json.loads(args.result.read_text()), args.out):
        print(f"wrote {path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
