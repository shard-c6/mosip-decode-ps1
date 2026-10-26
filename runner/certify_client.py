"""
Client for Inji Certify's own API: creating pre-authorized credential offers.

Issuer conformance modules, like verifier ones, are interactive: the suite plays the
wallet and waits for a credential offer to arrive at the `credential_offer_endpoint` it
exposes. In the pre-authorized flow the offer comes from the issuer, so the harness asks
Certify for one -- POST /pre-authorized-data, PreAuthorizedCodeController -- and hands it
over. Certify answers with exactly what a wallet would scan:

    openid-credential-offer://?credential_offer_uri=https%3A%2F%2F<host>%2Fv1%2Fcertify%2F...

and the suite's endpoint takes that same query string. Read from inji-certify
release-1.0.x (head 203b143).
"""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import parse_qsl, urlparse

import httpx

log = logging.getLogger(__name__)

OFFER_SCHEME = "openid-credential-offer"


class CertifyError(RuntimeError):
    pass


class InjiCertifyClient:
    def __init__(self, endpoint: str, timeout: int = 30, verify_ssl: bool = True) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._client = httpx.Client(timeout=timeout, verify=verify_ssl, follow_redirects=True)

    def create_pre_authorized_offer(
        self,
        credential_configuration_id: str,
        claims: dict[str, Any],
        expires_in: int = 600,
        tx_code: str | None = None,
    ) -> str:
        """
        Ask Certify for a pre-authorized credential offer; return the offer URI.

        `claims` must include every claim Certify's credential configuration marks
        mandatory (PreAuthorizedCodeService.validateClaims). Certify bounds `expires_in` to
        60..86400 seconds and `tx_code` to 4-8 alphanumerics.
        """
        body: dict[str, Any] = {
            "credential_configuration_id": credential_configuration_id,
            "claims": claims,
            "expires_in": expires_in,
        }
        if tx_code:
            body["tx_code"] = tx_code
        response = self._client.post(f"{self._endpoint}/pre-authorized-data", json=body)
        if response.status_code >= 400:
            raise CertifyError(
                f"/pre-authorized-data returned HTTP {response.status_code}: {response.text[:400]}"
            )
        offer_uri = (response.json() or {}).get("credential_offer_uri")
        if not offer_uri:
            raise CertifyError(f"/pre-authorized-data returned no credential_offer_uri: {response.text[:400]}")
        return offer_uri

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "InjiCertifyClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()


def offer_params(offer_uri: str) -> dict[str, str]:
    """
    The query parameters of an `openid-credential-offer://` URI -- `credential_offer_uri`
    (by reference, what Certify sends) or `credential_offer` (by value). These are what
    the suite's credential_offer_endpoint expects.
    """
    parsed = urlparse(offer_uri)
    if parsed.scheme != OFFER_SCHEME:
        raise CertifyError(f"not an {OFFER_SCHEME}:// URI: {offer_uri[:120]}")
    params = dict(parse_qsl(parsed.query, keep_blank_values=False))
    if not ({"credential_offer_uri", "credential_offer"} & params.keys()):
        raise CertifyError(f"offer URI carries neither credential_offer_uri nor credential_offer: {offer_uri[:120]}")
    return params
