"""
The result diff: identical runs compare equal even when ids and messages differ; a changed
result, verdict or failing check is reported; so is a module present in only one run.
"""

from __future__ import annotations

import copy
import json

import pytest

from runner import diff


def check(src: str, result: str, msg: str = "x") -> dict:
    return {"src": src, "result": result, "msg": msg}


@pytest.fixture
def run() -> dict:
    return {
        "run": {"runId": "run-a"},
        "components": [{"component": "inji-certify", "modules": [
            {"moduleName": "happy-flow", "testId": "A1", "result": "FAILED", "verdict": "PASS",
             "checks": [check("ValidateCredentialProof", "FAILURE"), check("CheckMetadata", "SUCCESS")]},
            {"moduleName": "fail-invalid-nonce", "testId": "A2", "result": "PASSED", "verdict": "PASS", "checks": []},
        ]}],
    }


def test_same_modules_with_different_ids_and_messages_compare_equal(run):
    other = copy.deepcopy(run)
    other["run"]["runId"] = "run-b"
    other["components"][0]["modules"][0]["testId"] = "B1"
    other["components"][0]["modules"][0]["checks"][0]["msg"] = "different text, same failure"
    assert diff.compare(run, other) == []
    assert "No differences" in diff.markdown(run, other, [])


def test_a_regression_is_reported(run):
    other = copy.deepcopy(run)
    m = other["components"][0]["modules"][1]
    m.update(result="FAILED", verdict="FAIL", checks=[check("CheckNonce", "FAILURE")])
    [change] = diff.compare(run, other)
    assert change["moduleName"] == "fail-invalid-nonce"
    assert "result PASSED → FAILED" in change["change"]
    assert "verdict PASS → FAIL" in change["change"]
    assert "new: CheckNonce FAILURE" in change["change"]


def test_a_fixed_check_is_reported(run):
    other = copy.deepcopy(run)
    other["components"][0]["modules"][0]["checks"] = []
    [change] = diff.compare(run, other)
    assert change["change"] == "no longer: ValidateCredentialProof FAILURE"


def test_modules_in_one_run_only(run):
    other = copy.deepcopy(run)
    other["components"][0]["modules"].pop()
    [change] = diff.compare(run, other)
    assert change["change"] == "only in the first run"


def test_exit_status(run, tmp_path):
    a, b = tmp_path / "a.json", tmp_path / "b.json"
    a.write_text(json.dumps(run))
    b.write_text(json.dumps(run))
    assert diff.main([str(a), str(b)]) == 0
    changed = copy.deepcopy(run)
    changed["components"][0]["modules"][1]["result"] = "FAILED"
    b.write_text(json.dumps(changed))
    assert diff.main([str(a), str(b), "--markdown", str(tmp_path / "d.md")]) == 1
    assert (tmp_path / "d.md").read_text().startswith("# Result diff")
    assert diff.main([str(a), str(tmp_path / "missing.json")]) == 2


def test_component_filter(run):
    combined = copy.deepcopy(run)
    combined["components"].append({"component": "inji-verify", "modules": [
        {"moduleName": "happy-flow", "result": "REVIEW", "verdict": "PASS", "checks": []}]})
    assert len(diff.compare(run, combined)) == 1
    assert diff.compare(run, diff.only(combined, "inji-certify")) == []
