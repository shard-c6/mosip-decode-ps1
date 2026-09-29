"""
Tests for the Inji Verify client: what the harness asks Verify for, and how.

These guard the two ways an automated run could silently measure something
different from the shipped product -- asking for the wrong credential, or sending a
different nonce than the shipped UI does.
"""

from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import httpx
import pytest

from runner import verify_client as vc

REPO_ROOT = Path(__file__).resolve().parent.parent
VERIFY_UI_CONFIG = REPO_ROOT.parent / "inji-verify" / "docker-compose" / "config" / "config.json"

# Real nonces observed on Day 1 (findings.tex, F-01). The reproduction must match
# their shape exactly, or an automated run is not measuring what a wallet receives.
DAY1_NONCES = ["MTc4OTg4MzIxMzQ5MA==", "MTc4OTg4NDUzNjY3OQ==", "MTc4OTg4NDY1NjQzNg=="]


def test_sdk_nonce_has_the_same_shape_as_the_real_day1_nonces():
    nonce = vc.sdk_compatible_nonce()
    for observed in DAY1_NONCES:
        assert len(nonce) == len(observed)
        assert nonce.endswith("==") and observed.endswith("==")  # the F-02 padding


def test_sdk_nonce_decodes_to_the_current_millisecond_clock():
    before = int(time.time() * 1000)
    decoded = int(base64.b64decode(vc.sdk_compatible_nonce()).decode())
    after = int(time.time() * 1000)
    assert before <= decoded <= after


def test_day1_nonces_really_are_timestamps():
    """The finding itself, re-checked from the evidence rather than trusted."""
    for observed in DAY1_NONCES:
        ms = int(base64.b64decode(observed).decode())
        assert 1_780_000_000_000 < ms < 1_800_000_000_000  # a 2026 epoch-millisecond


@pytest.mark.skipif(not VERIFY_UI_CONFIG.exists(), reason="sibling inji-verify clone not present")
def test_loads_the_mock_identity_definition_from_verifys_own_config():
    definition = vc.load_presentation_definition(VERIFY_UI_CONFIG, "Mock Identity (SD JWT)")
    fmt = definition["input_descriptors"][0]["format"]
    assert "vc+sd-jwt" in fmt


@pytest.mark.skipif(not VERIFY_UI_CONFIG.exists(), reason="sibling inji-verify clone not present")
def test_definition_is_wrapped_exactly_as_the_ui_wraps_it():
    """
    Regression test for the first live run's HTTP 400: verify-service requires an id,
    which the raw config definition lacks and the UI's envelope supplies.
    """
    definition = vc.load_presentation_definition(VERIFY_UI_CONFIG, "Mock Identity (SD JWT)")
    assert definition["id"] == "c4822b58-7fb4-454e-b827-f8758fe27f9a"  # Day 1's value
    assert set(definition) == {"id", "purpose", "input_descriptors"}   # UI drops `format`


@pytest.mark.skipif(not VERIFY_UI_CONFIG.exists(), reason="sibling inji-verify clone not present")
def test_unknown_credential_names_the_ones_that_exist():
    with pytest.raises(vc.VerifyError, match="Mock Identity"):
        vc.load_presentation_definition(VERIFY_UI_CONFIG, "No Such Credential")


def _client_capturing(captured: dict) -> vc.InjiVerifyClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = json.loads(request.content)
        captured["url"] = str(request.url)
        return httpx.Response(200, json={"requestId": "req_1", "expiresAt": 0})

    client = vc.InjiVerifyClient("http://verify.test/v1/verify")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_sdk_mode_sends_a_timestamp_nonce_and_the_definition():
    captured: dict = {}
    _client_capturing(captured).create_vp_session_request(
        client_id="inji-verify-ui", presentation_definition={"input_descriptors": []}, nonce_mode="sdk"
    )
    body = captured["body"]
    assert captured["url"].endswith("/vp-session-request")
    assert body["clientId"] == "inji-verify-ui"
    assert body["presentationDefinition"] == {"input_descriptors": []}
    assert body["nonce"].endswith("==")


def test_service_mode_sends_no_nonce_so_verify_generates_its_own():
    captured: dict = {}
    _client_capturing(captured).create_vp_session_request(
        client_id="inji-verify-ui", presentation_definition={"input_descriptors": []}, nonce_mode="service"
    )
    assert "nonce" not in captured["body"]


def test_a_request_without_any_definition_is_refused_before_calling_verify():
    with pytest.raises(vc.VerifyError, match="presentation definition"):
        vc.InjiVerifyClient("http://unused").create_vp_session_request(client_id="x")


def test_unknown_nonce_mode_is_refused():
    with pytest.raises(ValueError):
        vc.InjiVerifyClient("http://unused").create_vp_session_request(
            client_id="x", presentation_definition={}, nonce_mode="random"
        )


def test_by_reference_response_is_rejected_with_the_reason():
    with pytest.raises(vc.VerifyError, match="pre_registered"):
        vc.build_authorization_request_params({"requestId": "r", "requestUri": "https://x"})


def test_inline_response_becomes_query_params():
    params = vc.build_authorization_request_params({
        "requestId": "req_9",
        "authorizationDetails": {
            "clientId": "inji-verify-ui",
            "responseUri": "https://h/v1/verify/vp-submission/direct-post",
            "nonce": "abc",
            "presentationDefinition": {"id": "pd"},
        },
    })
    assert params["client_id"] == "inji-verify-ui"
    assert params["state"] == "req_9"
    assert json.loads(params["presentation_definition"]) == {"id": "pd"}
    assert "client_metadata" not in params  # never synthesised; see F-05
