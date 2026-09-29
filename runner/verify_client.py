"""
Client for Inji Verify's own API.

Verifier conformance modules need an authorization request from the component
under test. We generate it through Verify's `/vp-session-request` endpoint rather
than by driving its UI, which is what makes an unattended run possible.

The URI-building logic here is the library form of scripts/build-oid4vp-uri.py.
That script remains as a CLI because it is still the quickest way to debug a
handoff by hand.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

log = logging.getLogger(__name__)

# Inji Verify's Constants.DEFAULT_EXPIRY. An authorization request is dead 300
# seconds after issue, which is why the runner generates one only after the
# conformance module is already WAITING.
REQUEST_EXPIRY_SECONDS = 300


class VerifyError(RuntimeError):
    pass


class RequestExpired(VerifyError):
    """The authorization request died before it could be delivered."""


class InjiVerifyClient:
    def __init__(self, endpoint: str, timeout: int = 30, verify_ssl: bool = True) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._client = httpx.Client(timeout=timeout, verify=verify_ssl, follow_redirects=True)

    def create_vp_session_request(
        self,
        client_id: str,
        presentation_definition_id: str | None = None,
        transaction_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Ask Verify to mint an OID4VP authorization request.

        Returns the parsed response. `authorizationDetails` is present only in
        the inline (pre_registered) path; the `did` path delivers the request by
        reference via request_uri instead, which does not match the url_query
        variant the plan uses. See docs/CONTEXT.md section 3.
        """
        body: dict[str, Any] = {"clientId": client_id}
        if presentation_definition_id:
            body["presentationDefinitionId"] = presentation_definition_id
        if transaction_id:
            body["transactionId"] = transaction_id

        response = self._client.post(f"{self._endpoint}/vp-session-request", json=body)
        if response.status_code >= 400:
            raise VerifyError(
                f"vp-session-request returned HTTP {response.status_code}: {response.text[:400]}"
            )
        return response.json()

    def is_request_alive(self, request_id: str) -> bool:
        """
        Liveness check before delivering. Cheaper than discovering expiry from a
        confusing conformance failure -- which is exactly how test dgeeosZpIfDK1bA
        was lost on Day 1 and nearly filed as an Inji Verify defect.
        """
        response = self._client.get(f"{self._endpoint}/vp-request/{request_id}")
        return response.status_code == 200

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "InjiVerifyClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def seconds_until_expiry(session_response: dict[str, Any]) -> float | None:
    """Seconds left on this authorization request, or None if it does not say."""
    expires_at = session_response.get("expiresAt")
    if expires_at is None:
        return None
    return expires_at / 1000 - time.time()


def build_authorization_request_params(session_response: dict[str, Any]) -> dict[str, str]:
    """
    Turn Verify's /vp-session-request response into OID4VP authorization request
    query parameters, ready to hand to the conformance suite.

    Raises if handed a by-reference ('did') response, because its parameters live
    behind a request_uri the url_query variant will never dereference -- the
    mistake behind discarded test dMg4B5whxWgShIB.
    """
    details = session_response.get("authorizationDetails")
    if not details:
        raise VerifyError(
            "response has no 'authorizationDetails'. This is the by-reference "
            "('did' clientIdScheme) shape; the plan's url_query variant needs the "
            "inline ('pre_registered') shape. See docs/SETUP.md step 6."
        )

    params = {
        "client_id": details["clientId"],
        "response_type": details.get("responseType", "vp_token"),
        "response_mode": details.get("responseMode", "direct_post"),
        "response_uri": details["responseUri"],
        "nonce": details["nonce"],
    }

    # Inji Verify 0.18.2 sends presentation_definition (Presentation Exchange)
    # rather than dcql_query. Passing it through unchanged is deliberate: the
    # point of the run is to record what the component actually sends. See F-03.
    presentation_definition = details.get("presentationDefinition")
    if presentation_definition is not None:
        import json as _json

        params["presentation_definition"] = _json.dumps(
            presentation_definition, separators=(",", ":")
        )

    # client_metadata is absent from this response in the pre_registered path.
    # Whether Verify omits it or the UI adds it at QR-build time is unresolved
    # (finding F-05), so we forward it when present and never synthesise one --
    # inventing it here would make the harness the source of the very behaviour
    # the run is meant to measure.
    client_metadata = details.get("clientMetadata")
    if client_metadata is not None:
        import json as _json

        params["client_metadata"] = _json.dumps(client_metadata, separators=(",", ":"))

    state = session_response.get("requestId")
    if state:
        params["state"] = state

    return params
