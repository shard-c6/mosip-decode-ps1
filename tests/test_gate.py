"""
Gate tests.

The success path is the easy half. The failure path is the one that matters: a gate
that cannot fail is decoration, so every test here that asserts `passed is True` has
a sibling asserting it flips.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner import gate

PLAN = "oid4vp-1final-verifier-test-plan"
MODULE = "oid4vp-1final-verifier-happy-flow"


def baseline_with(expected: str) -> gate.Baseline:
    return gate.Baseline(
        data={
            "updatedAt": "2026-09-20T06:13:23Z",
            "components": {
                "inji-verify": {PLAN: {MODULE: {"expected": expected, "reason": "F-03"}}}
            },
        },
        path=Path("configs/contract/expected-failures.json"),
    )


def components_with(result: str | None, module_name: str = MODULE) -> list[dict]:
    return [
        {
            "component": "inji-verify",
            "plan": {"planName": PLAN},
            "modules": [{"moduleName": module_name, "result": result}],
        }
    ]


def test_known_failure_reports_pass_and_does_not_fail_the_build():
    """
    The case that needs justifying: a documented failure is no worse than baseline,
    so the build stays green. Verify's DCQL gap makes every module fail, and an
    absolute gate would be permanently red and therefore ignored.
    """
    components = components_with("FAILED")
    result = gate.apply(components, baseline_with("FAILED"))
    module = components[0]["modules"][0]
    assert module["verdict"] == "PASS"
    assert module["regression"] is False
    assert module["result"] == "FAILED"  # the suite's verdict is never rewritten
    assert result["passed"] is True


def test_regression_from_passing_baseline_fails_the_build():
    components = components_with("FAILED")
    result = gate.apply(components, baseline_with("PASSED"))
    module = components[0]["modules"][0]
    assert module["verdict"] == "FAIL"
    assert module["regression"] is True
    assert result["passed"] is False
    assert result["regressions"][0]["expected"] == "PASSED"
    assert result["regressions"][0]["actual"] == "FAILED"


def test_improvement_is_reported_but_never_fatal():
    components = components_with("PASSED")
    result = gate.apply(components, baseline_with("FAILED"))
    module = components[0]["modules"][0]
    assert module["improvement"] is True
    assert module["verdict"] == "PASS"
    assert result["passed"] is True
    assert len(result["improvements"]) == 1


def test_unknown_module_skips_rather_than_failing():
    """Failing on an unrecorded module would punish adding coverage."""
    components = components_with("FAILED", module_name="some-new-module")
    result = gate.apply(components, baseline_with("FAILED"))
    module = components[0]["modules"][0]
    assert module["verdict"] == "SKIP"
    assert result["passed"] is True
    assert result["unknownModules"][0]["moduleName"] == "some-new-module"


def test_warning_is_a_regression_against_a_passing_baseline():
    components = components_with("WARNING")
    result = gate.apply(components, baseline_with("PASSED"))
    assert result["passed"] is False


def test_absolute_policy_fails_on_the_same_data_the_default_passes():
    """Q4's other reading. Switching policy must change the verdict and nothing else."""
    components = components_with("FAILED")
    result = gate.apply(components, baseline_with("FAILED"), policy=gate.POLICY_ABSOLUTE)
    assert result["passed"] is False
    assert components[0]["modules"][0]["verdict"] == "FAIL"


def test_baseline_reason_is_carried_onto_the_module():
    components = components_with("FAILED")
    gate.apply(components, baseline_with("FAILED"))
    assert components[0]["modules"][0]["expectedReason"] == "F-03"


def test_missing_baseline_file_is_not_fatal():
    b = gate.Baseline.load(Path("/nonexistent/expected-failures.json"))
    assert b.data == {"components": {}}


def test_committed_baseline_parses_and_covers_the_day1_module():
    """Guards against the baseline and the runner drifting apart."""
    path = Path(__file__).resolve().parent.parent / "configs/contract/expected-failures.json"
    b = gate.Baseline.load(path)
    assert b.expected_for("inji-verify", PLAN, MODULE) == "FAILED"
    assert "F-03" in (b.reason_for("inji-verify", PLAN, MODULE) or "")


def test_human_summary_names_the_failing_module():
    components = components_with("FAILED")
    result = gate.apply(components, baseline_with("PASSED"))
    text = gate.summarise_for_humans(result)
    assert "GATE FAILED" in text
    assert MODULE in text
