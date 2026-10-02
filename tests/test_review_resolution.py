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
