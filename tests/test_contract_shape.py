"""
Guards the interface between the two halves of the project.

The runner's output and Mukta's OpenIDConformanceTest meet at exactly one place.
These tests assert that what the runner assembles has the same shape as the
committed fixture she builds against, so the two cannot drift apart silently.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import pytest

from runner import gate, normalise

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "configs" / "contract" / "example-run.json"

REQUIRED_MODULE_FIELDS = {
    "moduleName", "testId", "variant", "status", "result", "verdict", "expected",
    "regression", "improvement", "counts", "checks", "startedAt", "durationMs",
    "logUrl", "logFile", "logSignatureFile",
}
REQUIRED_CHECK_FIELDS = {"src", "result", "msg", "requirements", "detail", "findingRef"}
REQUIRED_GATE_FIELDS = {
    "policy", "baselineFile", "baselineUpdatedAt", "passed", "regressions",
    "improvements", "unknownModules", "harnessErrors",
}


@pytest.fixture(scope="module")
def fixture() -> dict:
    return json.loads(FIXTURE.read_text())


def test_fixture_has_the_documented_top_level_shape(fixture):
    assert fixture["schemaVersion"] == "1.0"
    assert {"run", "components", "gate"} <= set(fixture)


def test_fixture_module_carries_every_contract_field(fixture):
    module = fixture["components"][0]["modules"][0]
    missing = REQUIRED_MODULE_FIELDS - set(module)
    assert not missing, f"fixture is missing contract fields: {sorted(missing)}"


def test_fixture_checks_carry_every_contract_field(fixture):
    for check in fixture["components"][0]["modules"][0]["checks"]:
        missing = REQUIRED_CHECK_FIELDS - set(check)
        assert not missing, f"check {check.get('src')} missing: {sorted(missing)}"


def test_fixture_gate_carries_every_contract_field(fixture):
    missing = REQUIRED_GATE_FIELDS - set(fixture["gate"])
    assert not missing, f"gate missing: {sorted(missing)}"


def test_runner_output_matches_the_fixture_shape():
    """
    Build a module through the real code path and compare its key set to the
    fixture's. If this fails, the runner and the Java side have diverged.
    """
    matches = [
        p for p in glob.glob(str(REPO_ROOT / "logs" / "2026-09-20" / "*MtzpWoD2dVgtic0" / "*.json"))
        if not p.endswith(".sig")
    ]
    if not matches:
        pytest.skip("Day 1 log not present")
    raw = json.loads(Path(matches[0]).read_text())

    module = normalise.normalise_module(
        module_name="oid4vp-1final-verifier-happy-flow",
        module_id="MtzpWoD2dVgtic0",
        variant={},
        status="INTERRUPTED",
        result="FAILED",
        log=raw,
        suite_base_url="https://localhost.emobix.co.uk:8443",
    )
    components = [
        {"component": "inji-verify",
         "plan": {"planName": "oid4vp-1final-verifier-test-plan"},
         "modules": [module]}
    ]
    gate_result = gate.apply(
        components, gate.Baseline.load(REPO_ROOT / "configs/contract/expected-failures.json")
    )

    assert REQUIRED_MODULE_FIELDS <= set(module)
    assert REQUIRED_GATE_FIELDS <= set(gate_result)

    # The committed baseline records this module as an expected failure, so a run
    # reproducing Day 1 must be green.
    assert module["expected"] == "FAILED"
    assert module["verdict"] == "PASS"
    assert gate_result["passed"] is True


def test_summary_counts_are_consistent(fixture):
    summary = normalise.summarise(fixture["components"][0]["modules"])
    assert summary["total"] == len(fixture["components"][0]["modules"])
    assert summary["unexpectedFailures"] == 0
