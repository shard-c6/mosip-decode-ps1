"""
Client for Inji Verify's own API.

Verifier conformance modules need an authorization request from the component under
test. We generate it through Verify's session-request endpoint rather than by driving
its UI, which is what makes an unattended run possible.

The catch is fidelity. A wallet never receives what verify-service returns; it receives
what the UI's SDK builds from it. The SDK chooses the nonce, wraps or selects the query,
and adds parameters of its own when it builds the openid4vp:// URI. Bypass the SDK
naively and the harness measures something no wallet would ever see. Twice this has
mattered already: on 29 September a harness that sent no nonce would have made F-01/F-02
vanish, and on 2 October we found that the "client_metadata missing" warning behind F-05
was produced by our own tooling, because the SDK adds client_metadata at URI-build time
and we did not.

So the SDK's behaviour is reproduced here, per API generation, citing the source it was
read from. Two generations exist:

  0.18  Inji Verify 0.18.x. Presentation Exchange; /vp-session-request.
        Read from inji-verify master (0.18.x line) as cloned 18 Sep 2026.
  1.0   Inji Verify 1.0 line. DCQL; /v2/vp-session-request.
        Read from tag v1.0.0-alpha.1 (published images 1.0.0-alpha.1).
"""

from __future__ import annotations

import base64
import json
import logging
import secrets
import time
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

# Inji Verify's Constants.DEFAULT_EXPIRY. An authorization request is dead 300
# seconds after issue, which is why the runner generates one only after the
# conformance module is already WAITING.
REQUEST_EXPIRY_SECONDS = 300

API_0_18 = "0.18"
API_1_0 = "1.0"
API_VERSIONS = (API_0_18, API_1_0)

SESSION_REQUEST_PATH = {
    API_0_18: "/vp-session-request",
    API_1_0: "/v2/vp-session-request",  # inji-verify-sdk/src/utils/api.ts:137 at v1.0.0-alpha.1
}


class VerifyError(RuntimeError):
    pass


class RequestExpired(VerifyError):
    """The authorization request died before it could be delivered."""


# --------------------------------------------------------------------------------------
# Nonces
#
# Where the nonce in an authorization request comes from is a measurement decision, not
# a detail, so it is explicit and recorded in every run.
#
# The shipped product path is UI -> SDK -> verify-service. The SDK always supplies a
# nonce; verify-service generates its own only when none is supplied. So:
#
#   "sdk"     - reproduce what the SDK *of the version under test* sends. Measures the
#               deployed product. Default.
#   "service" - send no nonce; verify-service generates it. Measures the service alone.
#
# Running both is a controlled experiment. On 0.18.2 it confirmed F-01/F-02 live in the
# SDK. On the 1.0 line the two should agree, because both generators are random.
# --------------------------------------------------------------------------------------
NONCE_SDK = "sdk"
NONCE_SERVICE = "service"
NONCE_MODES = (NONCE_SDK, NONCE_SERVICE)


def sdk_nonce_0_18() -> str:
    """
    inji-verify-sdk 0.18.1, src/utils/api.ts lines 10-12:

        const generateNonce = (): string => btoa(Date.now().toString());

    Reproduced deliberately weak, so a run against 0.18.x measures what a real
    deployment sends a wallet. Not a recommendation. See F-01, F-02.
    """
    return base64.b64encode(str(int(time.time() * 1000)).encode()).decode()


# Kept under its original name: tests and the Day 4 evidence refer to it.
sdk_compatible_nonce = sdk_nonce_0_18


def sdk_nonce_1_0() -> str:
    """
    inji-verify-sdk at v1.0.0-alpha.1, src/utils/api.ts lines 17-26: 32 bytes from
    crypto.getRandomValues, base64url-encoded without padding. verify-service 1.0 also
    validates a supplied nonce: URL-safe characters only, at least 16 long
    (VPRequestCreateDto) -- so the 0.18-style nonce would be rejected outright.
    """
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()


SDK_NONCE = {API_0_18: sdk_nonce_0_18, API_1_0: sdk_nonce_1_0}


# --------------------------------------------------------------------------------------
# The query: what credential the verifier asks for
# --------------------------------------------------------------------------------------

# 0.18 only. The envelope verify-ui wraps selected credentials in before sending them,
# from verify-ui/src/redux/features/verify/vpVerificationState.ts lines 58-63. The id is
# a hard-coded constant in the UI -- every request from every deployment carries it.
UI_PRESENTATION_DEFINITION_ID = "c4822b58-7fb4-454e-b827-f8758fe27f9a"
UI_PRESENTATION_DEFINITION_PURPOSE = (
    "Relying party is requesting your digital ID for the purpose of Self-Authentication"
)


def _load_credential(config_file: Path | str, credential_name: str) -> dict[str, Any]:
    path = Path(config_file)
    if not path.exists():
        raise VerifyError(
            f"Inji Verify UI config not found at {path}. The harness expects the sibling "
            "clone layout in docs/SETUP.md, or uiConfigFile pointing at the right clone."
        )
    claims = json.loads(path.read_text()).get("verifiableClaims", [])
    for claim in claims:
        if claim.get("name") == credential_name:
            return claim
    names = ", ".join(c.get("name", "?") for c in claims)
    raise VerifyError(f"no credential named '{credential_name}' in {path}; found: {names}")


def load_presentation_definition(config_file: Path | str, credential_name: str) -> dict[str, Any]:
    """
    0.18: the presentation definition the shipped UI sends for this credential.

    The UI takes *only* `input_descriptors` from each selected credential
    (vpVerificationState.ts lines 82-83) and wraps them with a fixed id and purpose
    (lines 58-63); the credential's own top-level `format` is dropped. verify-service
    rejects a definition without an id (VPDefinitionResponseDto, @NotBlank) with a bare
    400 -- how the first live run failed on 29 September.
    """
    claim = _load_credential(config_file, credential_name)
    descriptors = (claim.get("definition") or {}).get("input_descriptors")
    if not descriptors:
        raise VerifyError(
            f"credential '{credential_name}' has no input_descriptors. If its config entry "
            "has a dcqlQuery instead, this is a 1.0-line config: set apiVersion to '1.0'."
        )
    return {
        "id": UI_PRESENTATION_DEFINITION_ID,
        "purpose": UI_PRESENTATION_DEFINITION_PURPOSE,
        "input_descriptors": descriptors,
    }


def load_dcql_query(config_file: Path | str, credential_name: str) -> dict[str, Any]:
    """1.0: the credential's dcqlQuery, sent as-is, as the 1.0 SDK does (api.ts:126-130)."""
    claim = _load_credential(config_file, credential_name)
    query = claim.get("dcqlQuery")
    if not query:
        raise VerifyError(
            f"credential '{credential_name}' has no dcqlQuery. If its config entry has a "
            "definition instead, this is a 0.18-line config: set apiVersion to '0.18'."
        )
    return query


def load_query(api_version: str, config_file: Path | str, credential_name: str) -> dict[str, Any]:
    _check_api(api_version)
    if api_version == API_0_18:
        return load_presentation_definition(config_file, credential_name)
    return load_dcql_query(config_file, credential_name)


def _check_api(api_version: str) -> None:
    if api_version not in API_VERSIONS:
        raise ValueError(f"apiVersion must be one of {API_VERSIONS}, got {api_version!r}")


# --------------------------------------------------------------------------------------
# client_metadata the SDK adds when it builds the request URI
# --------------------------------------------------------------------------------------

# 0.18: OpenID4VPVerification.tsx lines 66-81 (VPFormat), added unconditionally to inline
# requests at lines 124-130 as {client_name, vp_formats}. `vp_formats` is the pre-1.0-Final
# key name; 1.0 Final uses `vp_formats_supported`.
VP_FORMATS_0_18 = {
    "ldp_vp": {"proof_type": ["Ed25519Signature2018", "Ed25519Signature2020", "RsaSignature2018"]},
    "vc+sd-jwt": {
        "sd-jwt_alg_values": ["RS256", "ES256", "ES256K", "EdDSA"],
        "kb-jwt_alg_values": ["RS256", "ES256", "ES256K", "EdDSA"],
    },
}

# 1.0: OpenID4VPVerification.tsx lines 62-81 at v1.0.0-alpha.1 (VPFormatsSupported), added
# to inline requests only for decentralized_identifier: and redirect_uri: client ids
# (lines 116-123).
VP_FORMATS_SUPPORTED_1_0 = {
    "ldp_vp": {"proof_type": ["Ed25519Signature2018", "Ed25519Signature2020", "RsaSignature2018"]},
    "dc+sd-jwt": {
        "sd-jwt_alg_values": ["RS256", "ES256", "ES256K", "EdDSA"],
        "kb-jwt_alg_values": ["RS256", "ES256", "ES256K", "EdDSA"],
    },
    "vc+sd-jwt": {
        "sd-jwt_alg_values": ["RS256", "ES256", "ES256K", "EdDSA"],
        "kb-jwt_alg_values": ["RS256", "ES256", "ES256K", "EdDSA"],
    },
}


def _compact(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"))


# --------------------------------------------------------------------------------------
# The client
# --------------------------------------------------------------------------------------

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
        *,
        api_version: str = API_0_18,
        dcql_query: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Ask Verify to mint an OID4VP authorization request, the way its own SDK does.

        0.18 takes a presentation definition (or its id); 1.0 requires a dcql_query.
        Validated here, before calling Verify, because Verify's own validation answers
        with a bare 400 that says nothing about which field was wrong.
        """
        _check_api(api_version)
        if nonce_mode not in NONCE_MODES:
            raise ValueError(f"nonce_mode must be one of {NONCE_MODES}, got {nonce_mode!r}")

        body: dict[str, Any] = {"clientId": client_id}
        if api_version == API_0_18:
            if presentation_definition is None and presentation_definition_id is None:
                raise VerifyError(
                    "a presentation definition (or its id) is required: without one Verify "
                    "has no credential to ask the wallet for"
                )
            if presentation_definition is not None:
                body["presentationDefinition"] = presentation_definition
            if presentation_definition_id:
                body["presentationDefinitionId"] = presentation_definition_id
        else:
            if dcql_query is None:
                raise VerifyError("Inji Verify 1.0 requires a dcql_query (VPRequestCreateDto, @NotNull)")
            body["dcqlQuery"] = dcql_query

        if nonce_mode == NONCE_SDK:
            body["nonce"] = SDK_NONCE[api_version]()
        if transaction_id:
            body["transactionId"] = transaction_id

        url = self._endpoint + SESSION_REQUEST_PATH[api_version]
        response = self._client.post(url, json=body)
        if response.status_code >= 400:
            raise VerifyError(
                f"{SESSION_REQUEST_PATH[api_version]} returned HTTP {response.status_code}: "
                f"{response.text[:400]}"
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


def build_authorization_request_params(
    session_response: dict[str, Any],
    client_id: str | None = None,
    api_version: str = API_0_18,
) -> dict[str, str]:
    """
    The authorization request query parameters a wallet would receive, built exactly as
    the SDK of the version under test builds them from the session response
    (getPresentationDefinitionParams in OpenID4VPVerification.tsx).

    `client_id` is the SDK's configured client id; the SDK uses that, not a value from
    the response. When omitted, the response's own clientId is used.
    """
    _check_api(api_version)
    details = session_response.get("authorizationDetails")
    client_id = client_id or (details or {}).get("clientId")

    request_uri = session_response.get("requestUri")
    if request_uri:
        # By reference: the SDK sends client_id and request_uri only. The url_query test
        # variant never dereferences a request_uri -- the mistake behind discarded test
        # dMg4B5whxWgShIB -- so say so rather than let it fail obscurely.
        raise VerifyError(
            "Verify returned a by-reference request (requestUri). The plan's url_query "
            "variant needs the inline shape: use a credential whose client id prefix "
            "delivers inline (pre_registered). See docs/SETUP.md step 4b."
        )
    if not details:
        raise VerifyError(
            "response has neither 'authorizationDetails' nor 'requestUri'; the "
            "url_query variant needs the inline ('pre_registered') shape."
        )

    params: dict[str, str] = {"client_id": client_id}
    state = session_response.get("requestId")
    if state:
        params["state"] = state
    params["response_mode"] = details.get("responseMode", "direct_post")
    params["response_type"] = details.get("responseType", "vp_token")
    params["nonce"] = details["nonce"]
    params["response_uri"] = details["responseUri"]

    if api_version == API_0_18:
        # Inji Verify 0.18 sends presentation_definition (Presentation Exchange) rather
        # than dcql_query; forwarded unchanged, because the run must record what the
        # component sends. See F-03.
        if details.get("presentationDefinitionUri"):
            params["presentation_definition_uri"] = details["presentationDefinitionUri"]
        elif details.get("presentationDefinition") is not None:
            params["presentation_definition"] = _compact(details["presentationDefinition"])
        params["client_metadata"] = _compact({"client_name": client_id, "vp_formats": VP_FORMATS_0_18})
    else:
        if details.get("dcqlQuery") is not None:
            params["dcql_query"] = _compact(details["dcqlQuery"])
        if client_id.startswith(("decentralized_identifier:", "redirect_uri:")):
            params["client_metadata"] = _compact({"vp_formats_supported": VP_FORMATS_SUPPORTED_1_0})

    return params
