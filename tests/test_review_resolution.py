"""
REVIEW resolution: settling what the suite cannot see with the verifier's own verdict.

These pin the case that matters most: a verifier that accepts a forged credential must
fail the gate, even though the suite reports "REVIEW, 0 failures".
"""

from runner import gate, normalise

PLAN = "oid4vp-1final-verifier-test-plan"
ACCEPT_MSG = "Upload a screenshot showing that the verifier successfully verified the presented credential"
REJECT_MSG = "Upload a screenshot showing that the verifier reported the presented credential as invalid / rejected the presentation"


def module(msg, verdict, name="m"):
    m = {"moduleName": name, "result": "REVIEW", "status": "FINISHED",
         "checks": [{"src": "Expect", "result": "REVIEW", "msg": msg}],
         "verifierVerdict": verdict}
    m["reviewResolution"] = normalise.resolve_review(m)
    return m


def run_gate(mod, expected="REVIEW"):
    comps = [{"component": "inji-verify", "plan": {"planName": PLAN}, "modules": [mod]}]
    baseline = gate.Baseline({"components": {"inji-verify": {PLAN: {mod["moduleName"]: {"expected": expected}}}}})
    return gate.apply(comps, baseline)


def test_expectation_is_read_from_the_suites_own_message():
    assert normalise.review_expectation(module(ACCEPT_MSG, {})) == "accept"
    assert normalise.review_expectation(module(REJECT_MSG, {})) == "reject"


def test_forged_credential_accepted_fails_the_gate():
    m = module(REJECT_MSG, {"httpStatus": 200, "allChecksSuccessful": True})
    assert m["reviewResolution"] == {"expected": "reject", "verifier": "accepted", "consistent": False}
    result = run_gate(m)
    assert result["passed"] is False
    assert m["verdict"] == "FAIL"
    assert result["reviewMismatches"][0]["verifier"] == "accepted"
    assert "contradicts" in gate.summarise_for_humans(result)


def test_forged_credential_rejected_passes():
    m = module(REJECT_MSG, {"httpStatus": 200, "allChecksSuccessful": False})
    assert m["reviewResolution"]["consistent"] is True
    assert run_gate(m)["passed"] is True


def test_valid_credential_rejected_fails_the_gate():
    m = module(ACCEPT_MSG, {"httpStatus": 200, "allChecksSuccessful": False})
    assert run_gate(m)["passed"] is False


def test_unavailable_verdict_is_unknown_not_assumed():
    m = module(REJECT_MSG, {"httpStatus": 404})
    assert m["reviewResolution"]["verifier"] == "unknown"
    assert m["reviewResolution"]["consistent"] is None
    assert run_gate(m)["passed"] is True  # no evidence either way: baseline decides


def test_modules_not_in_review_are_not_resolved():
    m = {"moduleName": "x", "result": "PASSED", "checks": []}
    assert normalise.resolve_review(m) is None


def _failed_by_suite(verdict, name="present-revoked-credential"):
    m = module(REJECT_MSG, verdict, name)
    m["result"] = "FAILED"  # the suite saw the defect itself (here: status list never fetched)
    return m


def _gate_with_entry(mod, entry):
    comps = [{"component": "inji-verify", "plan": {"planName": PLAN}, "modules": [mod]}]
    return gate.apply(comps, gate.Baseline({"components": {"inji-verify": {PLAN: {mod["moduleName"]: entry}}}}))


def test_acknowledged_mismatch_failed_by_the_suite_passes_but_is_reported():
    """F-16: a revoked credential accepted, already FAILED by the suite, recorded as a finding."""
    m = _failed_by_suite({"httpStatus": 200, "allChecksSuccessful": True})
    result = _gate_with_entry(m, {"expected": "FAILED", "acknowledgedMismatch": "F-16"})
    assert result["passed"] is True
    assert m["verdict"] == "PASS"
    assert result["acknowledgedMismatches"][0]["finding"] == "F-16"
    assert "F-16" in gate.summarise_for_humans(result)


def test_acknowledgement_does_not_cover_a_contradiction_the_suite_cannot_see():
    """The reason the rule exists: REVIEW with a forged credential accepted always fails."""
    m = module(REJECT_MSG, {"httpStatus": 200, "allChecksSuccessful": True})
    result = _gate_with_entry(m, {"expected": "REVIEW", "acknowledgedMismatch": "F-16"})
    assert result["passed"] is False
    assert m["verdict"] == "FAIL"


def test_acknowledgement_needs_the_baseline_to_expect_failure():
    m = _failed_by_suite({"httpStatus": 200, "allChecksSuccessful": True})
    assert _gate_with_entry(m, {"expected": "PASSED", "acknowledgedMismatch": "F-16"})["passed"] is False


def test_mismatch_failed_by_the_suite_without_acknowledgement_still_fails():
    m = _failed_by_suite({"httpStatus": 200, "allChecksSuccessful": True})
    assert _gate_with_entry(m, {"expected": "FAILED"})["passed"] is False
