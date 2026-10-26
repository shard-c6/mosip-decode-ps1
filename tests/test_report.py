"""
The consolidated report: it must show the suite's result unchanged, the gate's verdict and
the reason for each, and a badge whose colour follows the gate -- for one component or two.
"""

from __future__ import annotations

import copy
import xml.dom.minidom

import pytest

from runner import report


def module(name: str, result: str, verdict: str, expected: str | None = None, **extra) -> dict:
    return {"moduleName": name, "result": result, "verdict": verdict, "expected": expected,
            "logUrl": f"https://suite/log-detail.html?log={name}", "checks": [], **extra}


@pytest.fixture
def combined() -> dict:
    return {
        "run": {"runId": "combined-x", "mode": "combined", "startedAt": "2026-10-26T16:16:04Z", "durationMs": 44742},
        "components": [
            {"component": "inji-verify", "role": "verifier", "version": "1.0.0-alpha.1",
             "endpoint": "http://localhost:8080/v1/verify",
             "plan": {"planId": "P1", "planName": "oid4vp-1final-verifier-test-plan", "planUrl": "https://suite/p1"},
             "modules": [module("happy-flow", "REVIEW", "PASS", "REVIEW")]},
            {"component": "inji-certify", "role": "issuer", "version": "1.0.x",
             "endpoint": "http://localhost:8090/v1/certify",
             "plan": {"planId": "P2", "planName": "oid4vci-1_0-issuer-test-plan", "planUrl": "https://suite/p2"},
             "modules": [
                 module("issuer-happy-flow", "FAILED", "PASS", "FAILED",
                        expectedReason="F-15: proof iss must be omitted"),
                 module("fail-invalid-nonce", "PASSED", "PASS", "PASSED"),
             ]},
        ],
        "gate": {"policy": "regression-from-baseline", "passed": True, "regressions": [],
                 "improvements": [], "unknownModules": [], "harnessErrors": [], "reviewMismatches": []},
    }


def failing(document: dict) -> dict:
    doc = copy.deepcopy(document)
    m = doc["components"][1]["modules"][1]
    m.update(result="FAILED", verdict="FAIL", regression=True)
    doc["gate"]["passed"] = False
    doc["gate"]["regressions"] = [{"component": "inji-certify", "moduleName": "fail-invalid-nonce"}]
    return doc


def test_markdown_covers_every_component_and_keeps_the_suite_result(combined):
    md = report.markdown(combined)
    assert "**Gate: PASSING**" in md
    assert "## Inji Verify" in md and "## Inji Certify" in md
    # A baselined failure: the suite's FAILED is shown, the gate's PASS beside it, with the reason.
    row = next(line for line in md.splitlines() if "issuer-happy-flow" in line)
    assert "| FAILED | FAILED | PASS | F-15: proof iss must be omitted |" in row


def test_failing_gate_names_the_regression(combined):
    md = report.markdown(failing(combined))
    assert "**Gate: FAILING**" in md
    assert "inji-certify / fail-invalid-nonce: regressed against the baseline" in md
    assert "Regression: expected PASSED, got FAILED" in md


def test_html_is_escaped(combined):
    combined["components"][1]["modules"][0]["expectedReason"] = "<script>alert(1)</script>"
    page = report.html_page(combined)
    assert "<script>" not in page and "&lt;script&gt;" in page


@pytest.mark.parametrize("make, colour, text", [
    (lambda d: d, "#2e7d32", "gate passing · 3 modules"),
    (failing, "#c62828", "gate failing · 1 problem(s)"),
])
def test_badge_follows_the_gate(combined, make, colour, text):
    svg = report.badge(make(combined))
    xml.dom.minidom.parseString(svg)  # well-formed
    assert colour in svg and text in svg
    assert "Certify ↔ Verify OpenID 1.0" in svg


def test_single_component_badge_names_it(combined):
    combined["components"] = combined["components"][1:]
    assert "Inji Certify OpenID 1.0" in report.badge(combined)


def test_write_produces_three_files(combined, tmp_path):
    names = sorted(p.name for p in report.write(combined, tmp_path / "out"))
    assert names == ["badge.svg", "report.html", "report.md"]
