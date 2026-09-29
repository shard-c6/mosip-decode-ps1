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

import base64
import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

# Inji Verify's Constants.DEFAULT_EXPIRY. An authorization request is dead 300
# seconds after issue, which is why the runner generates one only after the
# conformance module is already WAITING.
REQUEST_EXPIRY_SECONDS = 300


class VerifyError(RuntimeError):
    pass


# Where the nonce in an authorization request comes from. This is a measurement
# decision, not a detail, so it is explicit and recorded in every run.
#
# The shipped product path is UI -> SDK -> verify-service. The SDK always supplies
# a nonce, and verify-service only generates its own (SecurityUtils.generateNonce,
# SecureRandom over 16 bytes) when none is supplied. So:
#
#   "sdk"     - reproduce what the shipped UI sends. Measures the deployed product,
#               and is where findings F-01/F-02 live. Default.
#   "service" - send no nonce; verify-service generates it. Measures the service
#               alone.
#
# Running both is a controlled experiment: if the nonce findings appear only in
# "sdk" mode, that independently confirms the defect is in the SDK, not the service.
NONCE_SDK = "sdk"
NONCE_SERVICE = "service"
NONCE_MODES = (NONCE_SDK, NONCE_SERVICE)


def sdk_compatible_nonce() -> str:
    """
    A faithful reproduction of inji-verify-sdk 0.18.1, src/utils/api.ts lines 10-12:

        const generateNonce = (): string => btoa(Date.now().toString());

    It is reproduced -- deliberately weak -- so that an automated run measures what
    a real deployment sends a wallet. It is not a recommendation. See F-01, F-02 and
    docs/upstream/ISSUE-01-nonce-entropy.md.
    """
    return base64.b64encode(str(int(time.time() * 1000)).encode()).decode()


# The envelope verify-ui wraps selected credentials in before sending them, copied
# from verify-ui/src/redux/features/verify/vpVerificationState.ts lines 58-63 (0.18.2).
# The id is a hard-coded constant in the UI -- every request from every deployment
# carries the same one, which is why Day 1's request showed exactly this value.
UI_PRESENTATION_DEFINITION_ID = "c4822b58-7fb4-454e-b827-f8758fe27f9a"
UI_PRESENTATION_DEFINITION_PURPOSE = (
    "Relying party is requesting your digital ID for the purpose of Self-Authentication"
)


def load_presentation_definition(config_file: Path | str, credential_name: str) -> dict[str, Any]:
    """
    Build the presentation definition the shipped UI would send for this credential.

    Two sources, both read rather than restated:

      * the credential's input descriptors come from Inji Verify's own UI config
        (config/config.json), the file the UI itself loads; and
      * the envelope around them reproduces verify-ui's vpVerificationState.ts,
        which takes *only* `input_descriptors` from each selected credential
        (lines 82-83) and wraps them with a fixed id and purpose (lines 58-63).
        The credential's own top-level `format` is dropped by the UI, so it is
        dropped here too.

    verify-service rejects a definition without an `id` (VPDefinitionResponseDto,
    @NotBlank) with a bare 400 -- which is how the first live run failed on
    29 September when the raw config definition was sent unwrapped.
    """
    path = Path(config_file)
    if not path.exists():
        raise VerifyError(
            f"Inji Verify UI config not found at {path}. The harness expects the sibling "
            "clone layout in docs/SETUP.md (inji-verify next to mosip-decode-ps1)."
        )
    claims = json.loads(path.read_text()).get("verifiableClaims", [])
    for claim in claims:
        if claim.get("name") == credential_name:
            descriptors = (claim.get("definition") or {}).get("input_descriptors")
            if not descriptors:
                raise VerifyError(f"credential '{credential_name}' has no input_descriptors in {path}")
            return {
                "id": UI_PRESENTATION_DEFINITION_ID,
                "purpose": UI_PRESENTATION_DEFINITION_PURPOSE,
                "input_descriptors": descriptors,
            }
    names = ", ".join(c.get("name", "?") for c in claims)
    raise VerifyError(f"no credential named '{credential_name}' in {path}; found: {names}")


class RequestExpired(VerifyError):
    """The authorization request died before it could be delivered."""


class InjiVerifyClient:
    def __init__(self, endpoint: str, timeout: int = 30, verify_ssl: bool = True) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._client = httpx.Client(timeout=timeout, verify=verify_ssl, follow_redirects=True)

    def create_vp_session_request(
        self,
        client_id: str,
        presentation_definition: dict[str, Any] | None = None,
        presentation_definition_id: str | None = None,
        nonce_mode: str = NONCE_SDK,
        transaction_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Ask Verify to mint an OID4VP authorization request.

        Returns the parsed response. `authorizationDetails` is present only in
        the inline (pre_registered) path; the `did` path delivers the request by
        reference via request_uri instead, which does not match the url_query
        variant the plan uses. See docs/CONTEXT.md section 3.
        """
        if nonce_mode not in NONCE_MODES:
            raise ValueError(f"nonce_mode must be one of {NONCE_MODES}, got {nonce_mode!r}")
        if presentation_definition is None and presentation_definition_id is None:
            raise VerifyError(
                "a presentation definition (or its id) is required: without one Verify "
                "has no credential to ask the wallet for"
            )

        body: dict[str, Any] = {"clientId": client_id}
        if nonce_mode == NONCE_SDK:
            body["nonce"] = sdk_compatible_nonce()
        if presentation_definition is not None:
            body["presentationDefinition"] = presentation_definition
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
        params["presentation_definition"] = json.dumps(
            presentation_definition, separators=(",", ":")
        )

    # client_metadata is absent from this response in the pre_registered path.
    # Whether Verify omits it or the UI adds it at QR-build time is unresolved
    # (finding F-05), so we forward it when present and never synthesise one --
    # inventing it here would make the harness the source of the very behaviour
    # the run is meant to measure.
    client_metadata = details.get("clientMetadata")
    if client_metadata is not None:
        params["client_metadata"] = json.dumps(client_metadata, separators=(",", ":"))

    state = session_response.get("requestId")
    if state:
        params["state"] = state

    return params
