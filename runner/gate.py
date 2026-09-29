"""
The benchmark gate.

Inji Verify 0.18.2 fails every module of the OID4VP 1.0 Final verifier plan at DCQL
extraction (F-03). An absolute pass-rate gate would therefore be red permanently and
would be ignored within a week -- a gate nobody can act on is not a gate. So the
default policy fails the build on *change from a recorded baseline*, not on state.

The suite's own verdict is never altered: `result` keeps it and the Extent report
prints it. Only `verdict` -- what TestNG reports -- is gated. This is Q4 to mentors;
if MOSIP wants the absolute reading, `policy` switches and nothing else moves.

Pure: no network, no filesystem beyond the baseline the caller hands it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

POLICY_REGRESSION = "regression-from-baseline"
POLICY_ABSOLUTE = "absolute-pass-rate"

# Ordered best to worst. Used only to decide whether a change is a regression or
# an improvement; WARNING sits between because the suite treats it as a completed
# run that raised concerns.
_SEVERITY = {"PASSED": 0, "REVIEW": 1, "WARNING": 2, "SKIPPED": 3, "FAILED": 4}


@dataclass
class Baseline:
    """Expected results, keyed by component then plan then module."""

    data: dict[str, Any]
    path: Path | None = None

    @classmethod
    def load(cls, path: Path | str) -> "Baseline":
        path = Path(path)
        if not path.exists():
            return cls(data={"components": {}}, path=path)
        return cls(data=json.loads(path.read_text()), path=path)

    @property
    def updated_at(self) -> str | None:
        return self.data.get("updatedAt")

    def expected_for(self, component: str, plan_name: str, module_name: str) -> str | None:
        entry = (
            self.data.get("components", {})
            .get(component, {})
            .get(plan_name, {})
            .get(module_name)
        )
        if isinstance(entry, dict):
            return entry.get("expected")
        return entry if isinstance(entry, str) else None

    def reason_for(self, component: str, plan_name: str, module_name: str) -> str | None:
        entry = (
            self.data.get("components", {})
            .get(component, {})
            .get(plan_name, {})
            .get(module_name)
        )
        return entry.get("reason") if isinstance(entry, dict) else None


def _severity(result: str | None) -> int:
    return _SEVERITY.get(result or "", _SEVERITY["FAILED"])


def apply(
    components: list[dict[str, Any]],
    baseline: Baseline,
    policy: str = POLICY_REGRESSION,
) -> dict[str, Any]:
    """
    Fill each module's verdict/expected/regression/improvement, and return the
    run-level `gate` object. Mutates the module dicts in place.
    """
    regressions: list[dict[str, Any]] = []
    improvements: list[dict[str, Any]] = []
    unknown: list[dict[str, Any]] = []

    for component in components:
        name = component["component"]
        plan_name = component.get("plan", {}).get("planName", "")

        for module in component.get("modules", []):
            module_name = module["moduleName"]
            actual = module.get("result")
            expected = baseline.expected_for(name, plan_name, module_name)

            # Set these unconditionally rather than only on the branch that flips
            # them. The gate must not depend on normalise having pre-populated the
            # defaults: it is also applied to modules assembled elsewhere, and a
            # missing key there would read as a crash rather than "no regression".
            module["regression"] = False
            module["improvement"] = False
            module["expected"] = expected
            module["expectedReason"] = baseline.reason_for(name, plan_name, module_name)

            if policy == POLICY_ABSOLUTE:
                module["verdict"] = "PASS" if actual == "PASSED" else "FAIL"
                if actual != "PASSED":
                    regressions.append(_entry(name, module_name, expected, actual))
                continue

            if expected is None:
                # Surfaced, never fatal: a module nobody has recorded a baseline for
                # is an unreviewed result, and failing the build on it would punish
                # adding coverage.
                module["verdict"] = "SKIP"
                unknown.append(_entry(name, module_name, expected, actual))
                continue

            if _severity(actual) > _severity(expected):
                module["regression"] = True
                module["verdict"] = "FAIL"
                regressions.append(_entry(name, module_name, expected, actual))
            elif _severity(actual) < _severity(expected):
                module["improvement"] = True
                module["verdict"] = "PASS"
                improvements.append(_entry(name, module_name, expected, actual))
            else:
                module["verdict"] = "PASS"

    return {
        "policy": policy,
        "baselineFile": str(baseline.path) if baseline.path else None,
        "baselineUpdatedAt": baseline.updated_at,
        "passed": not regressions,
        "regressions": regressions,
        "improvements": improvements,
        "unknownModules": unknown,
    }


def _entry(component: str, module_name: str, expected: str | None, actual: str | None) -> dict[str, Any]:
    return {
        "component": component,
        "moduleName": module_name,
        "expected": expected,
        "actual": actual,
    }


def summarise_for_humans(gate: dict[str, Any]) -> str:
    """One-screen explanation, for CI output where nobody will open the JSON."""
    lines: list[str] = []
    if gate["passed"]:
        lines.append("GATE PASSED - no regressions against the recorded baseline.")
    else:
        lines.append(f"GATE FAILED - {len(gate['regressions'])} regression(s):")
        for r in gate["regressions"]:
            lines.append(
                f"  {r['component']} / {r['moduleName']}: "
                f"expected {r['expected']}, got {r['actual']}"
            )
    if gate["improvements"]:
        lines.append(
            f"{len(gate['improvements'])} module(s) improved on the baseline - "
            "update the expected-failures file:"
        )
        for i in gate["improvements"]:
            lines.append(
                f"  {i['component']} / {i['moduleName']}: "
                f"was {i['expected']}, now {i['actual']}"
            )
    if gate["unknownModules"]:
        lines.append(
            f"{len(gate['unknownModules'])} module(s) have no baseline entry "
            "(reported as SKIP, not fatal):"
        )
        for u in gate["unknownModules"]:
            lines.append(f"  {u['component']} / {u['moduleName']}: got {u['actual']}")
    return "\n".join(lines)
