"""
Client for the OpenID Foundation conformance suite's REST API.

This mirrors the endpoint surface of the suite's own `scripts/conformance.py`
(cloned at ../conformance-suite) and keeps its method names, so anyone who knows
that library can read this one. It is reimplemented rather than imported because:

  * the suite's scripts directory is not an installable package, and importing
    across a sibling clone would make the harness depend on a path that CI would
    have to reproduce;
  * we need two things it does not expose -- reading a test's exposed strings
    (to discover `authorization_endpoint`) and issuing the authorization-request
    handoff; and
  * its retry transport assumes the hosted deployment, where we need behaviour
    tuned to a local self-signed instance.

Retry semantics follow the suite's own RetryTransport: retry on transport errors
and 5xx, and on a JSON body that does not decode.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

from .config import SuiteConfig

log = logging.getLogger(__name__)

TERMINAL_STATES = {"FINISHED", "INTERRUPTED"}


class SuiteError(RuntimeError):
    """The suite returned something we cannot proceed from."""


class ConformanceSuite:
    def __init__(self, config: SuiteConfig) -> None:
        self._config = config
        base = config.base_url if config.base_url.endswith("/") else config.base_url + "/"
        self._base = base

        headers = {"Content-Type": "application/json"}
        if config.api_token:
            headers["Authorization"] = f"Bearer {config.api_token}"

        self._client = httpx.Client(
            verify=config.verify_ssl,
            timeout=config.timeout_seconds,
            headers=headers,
            follow_redirects=True,
        )

    # -- plumbing ---------------------------------------------------------

    def _request(
        self,
        method: str,
        path: str,
        *,
        expected: tuple[int, ...] = (200,),
        retries: int = 5,
        **kwargs: Any,
    ) -> httpx.Response:
        url = self._base + path.lstrip("/")
        last_error: str | None = None

        for attempt in range(1, retries + 1):
            if attempt > 2:
                time.sleep(1)
            try:
                response = self._client.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                last_error = f"transport error: {exc}"
                log.warning("%s %s failed (%s); retrying", method, url, exc)
                continue

            if 500 <= response.status_code < 600:
                last_error = f"HTTP {response.status_code}"
                log.warning("%s %s returned %d; retrying", method, url, response.status_code)
                continue

            if response.status_code not in expected:
                raise SuiteError(
                    f"{method} {url} returned HTTP {response.status_code}, "
                    f"expected one of {expected}: {response.text[:400]}"
                )
            return response

        raise SuiteError(f"{method} {url} failed after {retries} attempts: {last_error}")

    # -- plans and modules ------------------------------------------------

    def create_test_plan(
        self, plan_name: str, configuration: dict[str, Any], variant: dict[str, str] | None = None
    ) -> dict[str, Any]:
        params: dict[str, str] = {"planName": plan_name}
        if variant:
            params["variant"] = json.dumps(variant)
        response = self._request(
            "POST", "api/plan", params=params, content=json.dumps(configuration), expected=(201,)
        )
        return response.json()

    def create_test_from_plan(
        self, plan_id: str, module_name: str, variant: dict[str, str] | None = None
    ) -> dict[str, Any]:
        params: dict[str, str] = {"test": module_name, "plan": plan_id}
        if variant:
            params["variant"] = json.dumps(variant)
        return self._request("POST", "api/runner", params=params, expected=(201,)).json()

    def get_module_info(self, module_id: str) -> dict[str, Any]:
        return self._request("GET", f"api/info/{module_id}").json()

    def get_module_status(self, module_id: str) -> dict[str, Any]:
        """
        Runner-level view of a module. Unlike /api/info this carries `exposed`,
        which is where a verifier test publishes its authorization_endpoint.
        """
        return self._request("GET", f"api/runner/{module_id}").json()

    def get_test_log(self, module_id: str) -> list[dict[str, Any]] | dict[str, Any]:
        return self._request("GET", f"api/log/{module_id}").json()

    def wait_for_state(
        self, module_id: str, states: set[str], timeout: int = 300, poll_interval: float = 1.0
    ) -> str:
        """
        Block until the module reaches one of `states`.

        Uses /wait-state, which long-polls server-side, so this is cheap even
        with a generous timeout. Terminal states always end the wait: a module
        that has finished will never reach WAITING, and returning its real state
        lets the caller decide, rather than hanging until the timeout.
        """
        deadline = time.monotonic() + timeout
        while True:
            if time.monotonic() > deadline:
                raise TimeoutError(
                    f"module {module_id} did not reach {sorted(states)} within {timeout}s "
                    f"(last status: {self.get_module_info(module_id).get('status')})"
                )
            status = self.get_module_info(module_id).get("status")
            if status in states:
                return status
            if status in TERMINAL_STATES:
                return status
            time.sleep(poll_interval)

    def get_exposed(self, module_id: str) -> dict[str, Any]:
        """Strings a test publishes for the tester, e.g. authorization_endpoint."""
        return self.get_module_status(module_id).get("exposed", {}) or {}

    def deliver_authorization_request(self, authorization_endpoint: str, params: dict[str, str]) -> int:
        """
        The verifier-plan handoff.

        AbstractVP1FinalVerifierTest.start() exposes `authorization_endpoint` and
        states that the pasted request's "query string will be delivered to this
        test's authorization endpoint" -- handleHttp then dispatches path
        "authorize". So delivering the request is an ordinary HTTP GET with the
        verifier's query parameters. No browser and no form are involved; the
        suite's paste box is a convenience wrapper over exactly this call.

        Redirects are not followed: the suite answers with a redirect to the
        verifier's response_uri, and following it would have us, rather than the
        suite, complete the flow.
        """
        response = self._client.get(authorization_endpoint, params=params, follow_redirects=False)
        log.info("delivered authorization request -> HTTP %d", response.status_code)
        return response.status_code

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ConformanceSuite":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
