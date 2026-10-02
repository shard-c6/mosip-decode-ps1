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


def _inline_session(**details):
    base = {
        "clientId": "inji-verify-ui",
        "responseUri": "https://h/v1/verify/vp-submission/direct-post",
        "nonce": "abc",
    }
    base.update(details)
    return {"requestId": "req_9", "authorizationDetails": base}


def test_0_18_inline_response_becomes_query_params_with_sdk_client_metadata():
    """
    The 0.18 SDK adds client_metadata to every inline request when it builds the URI
    (OpenID4VPVerification.tsx:124-130). Until 2 October the harness did not, which is
    what produced the 'client_metadata missing' warning behind F-05.
    """
    params = vc.build_authorization_request_params(
        _inline_session(presentationDefinition={"id": "pd"}), client_id="inji-verify-ui"
    )
    assert params["client_id"] == "inji-verify-ui"
    assert params["state"] == "req_9"
    assert json.loads(params["presentation_definition"]) == {"id": "pd"}
    meta = json.loads(params["client_metadata"])
    assert meta["client_name"] == "inji-verify-ui"
    assert "vp_formats" in meta and "vp_formats_supported" not in meta  # pre-Final key name
    assert "dcql_query" not in params


def test_1_0_inline_response_carries_dcql_and_no_presentation_definition():
    params = vc.build_authorization_request_params(
        _inline_session(dcqlQuery={"credentials": [{"id": "x"}]}),
        client_id="inji-verify-ui", api_version="1.0",
    )
    assert json.loads(params["dcql_query"]) == {"credentials": [{"id": "x"}]}
    assert "presentation_definition" not in params
    # pre_registered client: the 1.0 SDK adds no client_metadata (lines 116-123)
    assert "client_metadata" not in params


def test_1_0_adds_vp_formats_supported_for_did_and_redirect_uri_clients():
    for client in ("decentralized_identifier:did:web:h:v1:verify", "redirect_uri:https://h/cb"):
        params = vc.build_authorization_request_params(
            _inline_session(dcqlQuery={}), client_id=client, api_version="1.0"
        )
        assert "vp_formats_supported" in json.loads(params["client_metadata"])


def test_by_reference_request_is_refused_with_the_fix():
    with pytest.raises(vc.VerifyError, match="pre_registered"):
        vc.build_authorization_request_params({"requestId": "r", "requestUri": "https://x"})


def test_1_0_sdk_nonce_is_random_url_safe_and_long_enough():
    a, b = vc.sdk_nonce_1_0(), vc.sdk_nonce_1_0()
    assert a != b
    assert len(a) >= 16 and "=" not in a  # verify-service 1.0 rejects anything else
    assert set(a) <= set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_")


def test_1_0_request_uses_v2_endpoint_and_dcql_body():
    captured: dict = {}
    _client_capturing(captured).create_vp_session_request(
        client_id="inji-verify-ui", api_version="1.0", dcql_query={"credentials": []}
    )
    assert captured["url"].endswith("/v2/vp-session-request")
    assert captured["body"]["dcqlQuery"] == {"credentials": []}
    assert "presentationDefinition" not in captured["body"]
    assert "=" not in captured["body"]["nonce"]


def test_1_0_request_without_dcql_is_refused_before_calling_verify():
    with pytest.raises(vc.VerifyError, match="dcql"):
        vc.InjiVerifyClient("http://unused").create_vp_session_request(client_id="x", api_version="1.0")


def test_wrong_generation_config_says_which_apiversion_to_use():
    if not VERIFY_UI_CONFIG.exists():
        pytest.skip("sibling inji-verify clone not present")
    with pytest.raises(vc.VerifyError, match="apiVersion"):
        vc.load_dcql_query(VERIFY_UI_CONFIG, "Mock Identity (SD JWT)")  # a 0.18 config


# --- Source-fidelity guards -----------------------------------------------------------
# The reproduction is only worth anything while it matches the SDK it was read from.
# These read the SDK source itself and fail if the constants drift.

SDK_0_18 = REPO_ROOT.parent / "inji-verify" / "inji-verify-sdk" / "src"


@pytest.mark.skipif(not SDK_0_18.exists(), reason="sibling inji-verify clone not present")
def test_0_18_reproduction_matches_the_sdk_source():
    api = (SDK_0_18 / "utils" / "api.ts").read_text()
    assert "btoa(Date.now().toString())" in api
    view = (SDK_0_18 / "components" / "openid4vp-verification" / "OpenID4VPVerification.tsx").read_text()
    assert '"client_metadata"' in view and "vp_formats: VPFormat" in view
    for alg in vc.VP_FORMATS_0_18["vc+sd-jwt"]["sd-jwt_alg_values"]:
        assert f'"{alg}"' in view
