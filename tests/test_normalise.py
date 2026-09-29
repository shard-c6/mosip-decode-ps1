"""
Normalisation tests, run against the real Day 1 conformance log.

Using the actual log rather than a hand-written sample matters: the suite's field
names are the contract's field names, and a fixture we invented would happily agree
with a wrong assumption about them.
"""

from __future__ import annotations

import glob
import json
from pathlib import Path

import pytest

from runner import normalise

REPO_ROOT = Path(__file__).resolve().parent.parent
DAY1_GLOB = str(REPO_ROOT / "logs" / "2026-09-20" / "*MtzpWoD2dVgtic0" / "*.json")


@pytest.fixture(scope="module")
def day1_log() -> dict:
    matches = [p for p in glob.glob(DAY1_GLOB) if not p.endswith(".sig")]
    if not matches:
        pytest.skip("Day 1 log not present")
    return json.loads(Path(matches[0]).read_text())


def test_split_log_handles_export_shape(day1_log):
    info, entries = normalise.split_log(day1_log)
    assert info["testId"] == "MtzpWoD2dVgtic0"
    assert info["testName"] == "oid4vp-1final-verifier-happy-flow"
    assert len(entries) == 34


def test_split_log_handles_bare_entry_list():
    """GET /api/log/{id} returns the list alone; both must work."""
    info, entries = normalise.split_log([{"src": "X", "result": "SUCCESS"}])
    assert info == {}
    assert len(entries) == 1


def test_counts_match_the_real_log(day1_log):
    _, entries = normalise.split_log(day1_log)
    counts = normalise.count_results(entries)
    assert counts == {"success": 15, "failure": 4, "warning": 3, "info": 7}


def test_checks_exclude_successes(day1_log):
    _, entries = normalise.split_log(day1_log)
    checks = normalise.extract_checks(entries)
    assert all(c["result"] != "SUCCESS" for c in checks)
    assert len(checks) == 15  # 4 failure + 3 warning + 7 info + 1 interrupted


def test_dcql_failure_maps_to_f03(day1_log):
    """The structural finding must be traceable from a CI message to the catalogue."""
    _, entries = normalise.split_log(day1_log)
    checks = normalise.extract_checks(entries)
    dcql = [c for c in checks if c["src"] == "ExtractDCQLQueryFromAuthorizationRequest"]
    assert len(dcql) == 1
    assert dcql[0]["result"] == "FAILURE"
    assert dcql[0]["findingRef"] == "F-03"
    assert dcql[0]["requirements"] == ["OID4VP-1FINAL-6"]


def test_detail_carries_suite_supplied_keys(day1_log):
    """Values like the measured entropy must survive; they are the evidence."""
    _, entries = normalise.split_log(day1_log)
    checks = normalise.extract_checks(entries)
    entropy = next(c for c in checks if c["src"] == "VP1FinalEnsureMinimumNonceEntropy")
    assert entropy["detail"]["actual"] == pytest.approx(73.68, abs=0.01)
    assert entropy["detail"]["expected"] == 96.0
    assert entropy["findingRef"] == "F-01"


def test_normalise_module_leaves_gate_fields_unset(day1_log):
    """Normalisation records what happened; gating decides what it means."""
    module = normalise.normalise_module(
        module_name="oid4vp-1final-verifier-happy-flow",
        module_id="MtzpWoD2dVgtic0",
        variant={},
        status="INTERRUPTED",
        result="FAILED",
        log=day1_log,
        suite_base_url="https://localhost.emobix.co.uk:8443",
    )
    assert module["result"] == "FAILED"
    assert module["verdict"] is None
    assert module["expected"] is None
    assert module["regression"] is False
    assert module["logUrl"].endswith("log-detail.html?log=MtzpWoD2dVgtic0")


def test_normalise_module_falls_back_to_testinfo(day1_log):
    """Status and result should come from the log when not supplied explicitly."""
    module = normalise.normalise_module(
        module_name="x", module_id="MtzpWoD2dVgtic0", variant={},
        status="", result=None, log=day1_log,
        suite_base_url="https://localhost.emobix.co.uk:8443",
    )
    assert module["status"] == "INTERRUPTED"
    assert module["result"] == "FAILED"
