"""
Turn the conformance suite's log into the contract shape in docs/CONTRACT.md.

Deliberately pure: no network, no clock, no filesystem. Everything it needs is an
argument, which is what makes it testable against the committed fixture built from
the real Day 1 log.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

# Log-entry `src` values mapped to our findings catalogue. This is what turns a CI
# failure message from a bare check name into "this is F-03, the documented DCQL
# gap", and it is what keeps docs/findings/findings.tex connected to the running
# system instead of drifting into a separate artefact.
FINDING_REFS: dict[str, str] = {
    "VP1FinalEnsureMinimumNonceEntropy": "F-01",
    "CheckForInvalidCharsInNonce": "F-02",
    "ExtractDCQLQueryFromAuthorizationRequest": "F-03",
    "CheckNoPresentationDefinitionInVpAuthorizationRequest": "F-04",
    "VP1FinalCheckForUnexpectedParametersInVpClientMetadata": "F-05",
    "VP1FinalValidateVpFormatsSupportedInClientMetadata": "F-05",
    "EnsureClientIdMatchesResponseUri": "F-09",
}

# Suite log fields we lift into named contract fields; everything else on an entry
# is carried through under `detail` so nothing the suite said is discarded.
_PROMOTED_FIELDS = {
    "_id", "alias", "baseMtlsUrl", "baseUrl", "config", "planId", "testId",
    "testName", "testOwner", "variant", "time", "src", "result", "msg",
    "requirements", "description",
}

_INTERESTING_RESULTS = {"FAILURE", "WARNING", "INFO", "INTERRUPTED", "REVIEW"}


def split_log(log: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Accept either shape the suite produces.

    A downloaded export is {"testInfo": ..., "results": [...]}; GET /api/log/{id}
    returns the bare entry list. Handling both means an archived log and a live
    fetch can go through the same code path.
    """
    if isinstance(log, dict):
        return log.get("testInfo", {}) or {}, log.get("results", []) or []
    return {}, list(log or [])


def extract_checks(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Every non-SUCCESS log entry, in the contract's `checks` shape."""
    checks = []
    for entry in entries:
        result = entry.get("result")
        if result not in _INTERESTING_RESULTS:
            continue
        checks.append(
            {
                "src": entry.get("src"),
                "result": result,
                "msg": entry.get("msg"),
                "requirements": entry.get("requirements", []),
                "detail": {k: v for k, v in entry.items() if k not in _PROMOTED_FIELDS},
                "findingRef": FINDING_REFS.get(entry.get("src")),
            }
        )
    return checks


def count_results(entries: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(e.get("result") for e in entries)
    return {
        "success": counts.get("SUCCESS", 0),
        "failure": counts.get("FAILURE", 0),
        "warning": counts.get("WARNING", 0),
        "info": counts.get("INFO", 0),
    }


def normalise_module(
    *,
    module_name: str,
    module_id: str,
    variant: dict[str, str],
    status: str,
    result: str | None,
    log: Any,
    suite_base_url: str,
    log_file: str | None = None,
    started_at: str | None = None,
    duration_ms: int | None = None,
) -> dict[str, Any]:
    """
    One conformance module as one contract entry.

    `verdict`, `expected`, `regression` and `improvement` are left for the gate to
    fill: normalisation records what happened, gating decides what it means. Keeping
    those apart is what lets a known failure be reported as a TestNG pass without
    this layer ever claiming the suite passed.
    """
    test_info, entries = split_log(log)
    effective_result = result or test_info.get("result")
    effective_status = status or test_info.get("status")

    base = suite_base_url.rstrip("/")
    return {
        "moduleName": module_name,
        "testId": module_id,
        "variant": variant or test_info.get("variant", {}),
        "status": effective_status,
        "result": effective_result,
        "verdict": None,
        "expected": None,
        "regression": False,
        "improvement": False,
        "counts": count_results(entries),
        "checks": extract_checks(entries),
        "startedAt": started_at or test_info.get("started"),
        "durationMs": duration_ms,
        "logUrl": f"{base}/log-detail.html?log={module_id}",
        "logFile": log_file,
        "logSignatureFile": f"{log_file}.sig" if log_file else None,
    }


def review_expectation(module: dict[str, Any]) -> str | None:
    """
    What a REVIEW-state module is waiting for a human to confirm: that the verifier
    accepted the presentation ("accept") or rejected it ("reject"). Read from the suite's
    own REVIEW message, e.g. "...the verifier successfully verified the presented
    credential" versus "...reported the presented credential as invalid / rejected...".
    """
    for check in module.get("checks", []):
        if check.get("result") != "REVIEW":
            continue
        msg = (check.get("msg") or "").lower()
        if "invalid" in msg or "rejected" in msg:
            return "reject"
        if "successfully verified" in msg:
            return "accept"
    return None


def resolve_review(module: dict[str, Any]) -> dict[str, Any] | None:
    """
    Settle a REVIEW with evidence the suite cannot see: the verifier's own verdict.

    The suite stops at REVIEW because OID4VP 1.0 Final lets a verifier accept a
    submission and verify it afterwards, so whether a forged credential was rejected is
    invisible to it. The harness controls the verifier side and can fetch the verdict
    (verifierVerdict). Without this, a verifier that accepted forged credentials would
    report "REVIEW, 0 failures".

    Returns None for modules not in REVIEW. `consistent` is None when the verdict could
    not be obtained -- unknown, never assumed either way.
    """
    expected = review_expectation(module)
    if expected is None:
        return None
    verdict = module.get("verifierVerdict") or {}
    ok = verdict.get("allChecksSuccessful")
    verifier = "accepted" if ok is True else "rejected" if ok is False else "unknown"
    consistent = None if verifier == "unknown" else (
        (expected == "accept") == (verifier == "accepted")
    )
    return {"expected": expected, "verifier": verifier, "consistent": consistent}


def summarise(modules: list[dict[str, Any]]) -> dict[str, int]:
    """Component-level counts. Call after gating so the gate fields are populated."""
    return {
        "total": len(modules),
        "passed": sum(1 for m in modules if m.get("result") == "PASSED"),
        "failed": sum(1 for m in modules if m.get("result") == "FAILED"),
        "warning": sum(1 for m in modules if m.get("result") == "WARNING"),
        "skipped": sum(1 for m in modules if m.get("verdict") == "SKIP"),
        "expectedFailures": sum(
            1 for m in modules if m.get("expected") == "FAILED" and m.get("result") == "FAILED"
        ),
        "unexpectedFailures": sum(1 for m in modules if m.get("regression")),
        "newPasses": sum(1 for m in modules if m.get("improvement")),
    }
