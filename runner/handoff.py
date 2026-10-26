"""
The interactive handoff: getting a verifier's authorization request into a WAITING
conformance module.

Verifier plans are inverted relative to issuer plans. The suite plays the wallet and
waits passively; the verifier must initiate. The suite's UI presents this as a box to
paste an `openid4vp://` URI into, which is why the flow has been manual until now.

Reading the suite's source settles how to do it without a browser.
AbstractVP1FinalVerifierTest.start() does:

    getBrowser().requestUriInput(env.getString("authorization_endpoint"),
        "Paste the openid4vp:// authorization request produced by the verifier under
         test; its query string will be delivered to this test's authorization endpoint.")

and handleHttp() dispatches path "authorize". So the paste box is a convenience
wrapper over an ordinary HTTP GET to the exposed `authorization_endpoint` carrying
the verifier's query parameters. That is what deliver() does.

This module is deliberately separate. It is the piece most likely to need a
semi-automated fallback, and isolating it means the fallback is a swapped
implementation rather than a rewrite.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .suite import ConformanceSuite

if False:  # typing only
    from .certify_client import InjiCertifyClient  # noqa: F401
from .verify_client import (
    API_0_18,
    NONCE_SDK,
    InjiVerifyClient,
    RequestExpired,
    build_authorization_request_params,
    seconds_until_expiry,
)

log = logging.getLogger(__name__)

# Below this, delivering is a coin flip: Verify's request expires 300s after issue
# and a slow suite round trip can consume what remains. Better to fail loudly than
# to produce a conformance failure that looks like a component defect -- which is
# exactly what happened to test dgeeosZpIfDK1bA on Day 1.
MIN_REMAINING_SECONDS = 30


class HandoffError(RuntimeError):
    """The authorization request could not be delivered to the module."""


@dataclass
class HandoffResult:
    delivered: bool
    http_status: int | None
    request_id: str | None
    seconds_remaining: float | None
    nonce_mode: str = NONCE_SDK
    api_version: str = API_0_18
    detail: str = ""
    # Binds this session to its verdict. Deliberately not in as_contract(): it is a
    # session credential, and the verdict itself is what gets recorded.
    session_cookie: str | None = None

    def as_contract(self) -> dict[str, Any]:
        """The `handoff` block recorded on each verifier module."""
        return {
            "delivered": self.delivered,
            "httpStatus": self.http_status,
            "requestId": self.request_id,
            "secondsRemaining": round(self.seconds_remaining) if self.seconds_remaining is not None else None,
            "nonceMode": self.nonce_mode,
            "apiVersion": self.api_version,
        }


def deliver(
    suite: ConformanceSuite,
    verify: InjiVerifyClient,
    module_id: str,
    client_id: str,
    presentation_definition: dict[str, Any] | None = None,
    presentation_definition_id: str | None = None,
    nonce_mode: str = NONCE_SDK,
    api_version: str = API_0_18,
    dcql_query: dict[str, Any] | None = None,
) -> HandoffResult:
    """
    Generate an authorization request and deliver it to a WAITING module.

    Order matters and is not negotiable: the module must already be WAITING before
    Verify mints the request, because the 300-second expiry starts at issue. Minting
    first burns the budget on the suite's startup.
    """
    exposed = suite.get_exposed(module_id)
    authorization_endpoint = exposed.get("authorization_endpoint")
    if not authorization_endpoint:
        raise HandoffError(
            f"module {module_id} exposes no authorization_endpoint "
            f"(exposed keys: {sorted(exposed)}). Either it is not a verifier test, "
            "or it has not reached WAITING yet."
        )

    session = verify.create_vp_session_request(
        client_id=client_id,
        presentation_definition=presentation_definition,
        presentation_definition_id=presentation_definition_id,
        nonce_mode=nonce_mode,
        api_version=api_version,
        dcql_query=dcql_query,
    )
    request_id = session.get("requestId")
    remaining = seconds_until_expiry(session)

    if remaining is not None and remaining < MIN_REMAINING_SECONDS:
        raise RequestExpired(
            f"authorization request {request_id} has {remaining:.0f}s left, "
            f"below the {MIN_REMAINING_SECONDS}s floor. Not delivering; a failure "
            "here would look like a component defect rather than a timing artefact."
        )

    params = build_authorization_request_params(session, client_id=client_id, api_version=api_version)
    status = suite.deliver_authorization_request(authorization_endpoint, params)

    log.info(
        "handoff: module=%s request=%s remaining=%ss -> HTTP %s",
        module_id,
        request_id,
        f"{remaining:.0f}" if remaining is not None else "unknown",
        status,
    )

    return HandoffResult(
        delivered=True,
        http_status=status,
        request_id=request_id,
        seconds_remaining=remaining,
        nonce_mode=nonce_mode,
        api_version=api_version,
        session_cookie=verify.session_cookie,
    )


# ---------------------------------------------------------------------------------------
# Issuer side
# ---------------------------------------------------------------------------------------

def deliver_credential_offer(
    suite: ConformanceSuite,
    certify: "InjiCertifyClient",
    module_id: str,
    credential_configuration_id: str,
    claims: dict[str, Any],
    tx_code: str | None = None,
) -> HandoffResult:
    """
    The issuer-plan handoff, for the pre-authorized flow.

    The suite plays the wallet. AbstractVCIIssuerTestModule.waitForCredentialOffer()
    exposes `credential_offer_endpoint` and handleHttp() dispatches path
    "credential_offer" -- the same shape as the verifier handoff. The harness asks Certify
    for a fresh offer and delivers its query string to that endpoint by HTTP GET, as a
    wallet scanning Certify's QR code would.
    """
    from .certify_client import offer_params

    exposed = suite.get_exposed(module_id)
    endpoint = exposed.get("credential_offer_endpoint")
    if not endpoint:
        raise HandoffError(
            f"module {module_id} exposes no credential_offer_endpoint "
            f"(exposed keys: {sorted(exposed)}). It is not waiting for an offer."
        )
    offer_uri = certify.create_pre_authorized_offer(credential_configuration_id, claims, tx_code=tx_code)
    status = suite.deliver_authorization_request(endpoint, offer_params(offer_uri))
    log.info("issuer handoff: module=%s config=%s -> HTTP %s", module_id, credential_configuration_id, status)
    return HandoffResult(delivered=True, http_status=status, request_id=None, seconds_remaining=None,
                         detail="pre-authorized credential offer")


def deliver_tx_code(suite: ConformanceSuite, module_id: str, tx_code: str) -> HandoffResult:
    """
    Answer a module waiting for a transaction code. The suite exposes
    `tx_code_endpoint` as `<base>/tx_code?code=your_tx_code`
    (AbstractVCIIssuerTestModule.waitForTxCode); the code goes in that query parameter.
    """
    from urllib.parse import urlsplit, urlunsplit

    endpoint = suite.get_exposed(module_id).get("tx_code_endpoint")
    if not endpoint:
        raise HandoffError(f"module {module_id} exposes no tx_code_endpoint")
    base = urlunsplit(urlsplit(endpoint)._replace(query=""))
    status = suite.deliver_authorization_request(base, {"code": tx_code})
    log.info("tx_code handoff: module=%s -> HTTP %s", module_id, status)
    return HandoffResult(delivered=True, http_status=status, request_id=None, seconds_remaining=None,
                         detail="tx_code")
