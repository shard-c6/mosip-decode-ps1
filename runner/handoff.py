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
from .verify_client import (
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
    detail: str = ""


def deliver(
    suite: ConformanceSuite,
    verify: InjiVerifyClient,
    module_id: str,
    client_id: str,
    presentation_definition_id: str | None = None,
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
        client_id=client_id, presentation_definition_id=presentation_definition_id
    )
    request_id = session.get("requestId")
    remaining = seconds_until_expiry(session)

    if remaining is not None and remaining < MIN_REMAINING_SECONDS:
        raise RequestExpired(
            f"authorization request {request_id} has {remaining:.0f}s left, "
            f"below the {MIN_REMAINING_SECONDS}s floor. Not delivering; a failure "
            "here would look like a component defect rather than a timing artefact."
        )

    params = build_authorization_request_params(session)
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
    )
