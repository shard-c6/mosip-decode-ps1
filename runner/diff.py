"""
Result diff between two runs.

Compares two result documents module by module and says what changed: a module's suite
result, the gate's verdict, or the set of checks that did not succeed (by condition name
and outcome; messages are ignored, since they carry ids and timestamps that differ on
every run). Modules present in only one run are listed too.

    python -m runner.diff results/before.json results/after.json [--component NAME] [--markdown FILE]

Exit status: 0 when the two runs are the same, 1 when anything differs, 2 on bad input.
Used to show a combined run matches the standalone runs, and that a new release changes
only what it was meant to.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Check outcomes that make a module what it is; SUCCESS and INFO lines are not compared.
_NOTABLE = {"FAILURE", "WARNING", "REVIEW", "SKIPPED", "INTERRUPTED"}


def _signature(module: dict[str, Any]) -> dict[str, Any]:
    checks = sorted(
        {(c.get("src") or "?", c.get("result")) for c in module.get("checks", []) if c.get("result") in _NOTABLE}
    )
    return {"result": module.get("result"), "verdict": module.get("verdict"), "checks": checks}


def _modules(document: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    return {
        (c.get("component", "?"), m.get("moduleName", "?")): _signature(m)
        for c in document.get("components", [])
        for m in c.get("modules", [])
    }


def only(document: dict[str, Any], component: str) -> dict[str, Any]:
    """The document restricted to one component, e.g. to compare it with a single-component run."""
    return {**document, "components": [c for c in document.get("components", []) if c.get("component") == component]}


def compare(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """One entry per module that differs: what it was, what it is, and what changed."""
    a, b = _modules(before), _modules(after)
    changes = []
    for key in sorted(a.keys() | b.keys()):
        old, new = a.get(key), b.get(key)
        if old == new:
            continue
        entry: dict[str, Any] = {"component": key[0], "moduleName": key[1]}
        if old is None:
            entry["change"] = "only in the second run"
        elif new is None:
            entry["change"] = "only in the first run"
        else:
            parts = []
            for field in ("result", "verdict"):
                if old[field] != new[field]:
                    parts.append(f"{field} {old[field]} → {new[field]}")
            gone = [c for c in old["checks"] if c not in new["checks"]]
            came = [c for c in new["checks"] if c not in old["checks"]]
            if gone:
                parts.append("no longer: " + ", ".join(f"{src} {res}" for src, res in gone))
            if came:
                parts.append("new: " + ", ".join(f"{src} {res}" for src, res in came))
            entry["change"] = "; ".join(parts)
        changes.append(entry)
    return changes


def markdown(before: dict[str, Any], after: dict[str, Any], changes: list[dict[str, Any]]) -> str:
    def name(doc: dict[str, Any]) -> str:
        return f"`{doc.get('run', {}).get('runId', '?')}`"

    total = len(_modules(before) | _modules(after))
    lines = [f"# Result diff: {name(before)} → {name(after)}", ""]
    if not changes:
        lines.append(f"**No differences** across {total} modules: same suite results, same gate verdicts, "
                     "same checks not succeeding.")
    else:
        lines += [f"**{len(changes)} of {total} modules differ.**", "",
                  "| Component | Module | What changed |", "|---|---|---|"]
        lines += [f"| {c['component']} | {c['moduleName']} | {c['change']} |" for c in changes]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m runner.diff", description=__doc__.split("\n\n")[0])
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--component", help="compare only this component (e.g. inji-certify)")
    parser.add_argument("--markdown", type=Path, help="also write the diff as Markdown here")
    args = parser.parse_args(argv)
    try:
        before, after = (json.loads(p.read_text()) for p in (args.before, args.after))
    except (OSError, ValueError) as exc:
        print(f"cannot read result: {exc}", file=sys.stderr)
        return 2
    if args.component:
        before, after = only(before, args.component), only(after, args.component)
    changes = compare(before, after)
    text = markdown(before, after, changes)
    print(text, end="")
    if args.markdown:
        args.markdown.write_text(text)
    return 1 if changes else 0


if __name__ == "__main__":
    sys.exit(main())
