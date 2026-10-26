"""The Inji Certify client and the issuer-side plan configuration."""

from __future__ import annotations

import json

import httpx
import pytest

from runner import certify_client as cc
from runner.orchestrator import resolve_plan_config

REAL_OFFER = ("openid-credential-offer://?credential_offer_uri=https%3A%2F%2Fhost.example%2Fv1%2Fcertify"
              "%2Fcredential-offer-data%2Fb811dfa6-5f84-41ab-a49f-2d9d5863e52e")  # shape Certify returned


def test_offer_params_decode_the_uri_certify_returns():
    assert cc.offer_params(REAL_OFFER) == {
        "credential_offer_uri": "https://host.example/v1/certify/credential-offer-data/b811dfa6-5f84-41ab-a49f-2d9d5863e52e"
    }


def test_offer_params_reject_anything_but_an_offer_uri():
    with pytest.raises(cc.CertifyError):
        cc.offer_params("openid4vp://?client_id=x")
    with pytest.raises(cc.CertifyError):
        cc.offer_params("openid-credential-offer://?foo=bar")


def _client(captured: dict, status: int = 201, body: dict | None = None) -> cc.InjiCertifyClient:
    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(status, json=body if body is not None else {"credential_offer_uri": REAL_OFFER})
    client = cc.InjiCertifyClient("http://certify.test/v1/certify")
    client._client = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_create_offer_posts_the_documented_body_with_tx_code():
    captured: dict = {}
    uri = _client(captured).create_pre_authorized_offer("Cfg", {"fullName": "A"}, expires_in=300, tx_code="4815")
    assert uri == REAL_OFFER
    assert captured["url"].endswith("/pre-authorized-data")
    assert captured["body"] == {"credential_configuration_id": "Cfg", "claims": {"fullName": "A"},
                                "expires_in": 300, "tx_code": "4815"}


def test_create_offer_surfaces_certify_errors():
    with pytest.raises(cc.CertifyError, match="HTTP 400"):
        _client({}, status=400, body={"error": "x"}).create_pre_authorized_offer("Cfg", {})


def test_every_key_file_reference_is_resolved(tmp_path):
    (tmp_path / "c.json").write_text(json.dumps({"keys": [{"kty": "EC", "d": "S"}]}))
    (tmp_path / "s.json").write_text(json.dumps({"kty": "EC", "d": "S2"}))
    out = resolve_plan_config({"client": {"client_id": "w", "jwks_file": "c.json"},
                               "credential": {"signing_jwk_file": "s.json"}}, tmp_path)
    assert out["client"] == {"client_id": "w", "jwks": {"keys": [{"kty": "EC", "d": "S"}]}}
    assert out["credential"]["signing_jwk"]["d"] == "S2"
