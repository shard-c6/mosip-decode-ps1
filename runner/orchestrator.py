"""
Runs plans against components and assembles the contract document.
"""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from . import __version__, gate, normalise
from .redact import redact
from .config import ComponentConfig, RunnerConfig
from .handoff import HandoffError, deliver, deliver_credential_offer, deliver_tx_code
from .suite import ConformanceSuite, SuiteError
from .certify_client import CertifyError, InjiCertifyClient
from .verify_client import (
    InjiVerifyClient,
    RequestExpired,
    API_0_18,
    API_1_0,
    VerifyError,
    load_query,
)

log = logging.getLogger(__name__)

WAITING_STATES = {"WAITING"}
TERMINAL_STATES = {"FINISHED", "INTERRUPTED"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class ModuleFailure(RuntimeError):
    """
    A module could not be executed, as distinct from a module that ran and failed.

    The difference matters: a conformance failure is a finding about the component,
    a harness failure is a bug in us. Collapsing them would let our own breakage be
    recorded as evidence against MOSIP.
    """


def _strip_comments(value: Any) -> Any:
    """Drop our `_comment...` annotations: they document the config, not the suite's input."""
    if isinstance(value, dict):
        return {k: _strip_comments(v) for k, v in value.items() if not k.startswith("_comment")}
    if isinstance(value, list):
        return [_strip_comments(v) for v in value]
    return value


def resolve_plan_config(plan_config: dict[str, Any], repo_root: Path) -> dict[str, Any]:
    """
    Turn file references in the plan configuration into their contents.

    The suite needs private keys inline in the plan configuration -- `credential.signing_jwk`
    for the verifier plan, `client.jwks` for the issuer plan. Private key material must not
    sit in a committed file, so the committed config names a file instead: any key ending
    in `_file` (`signing_jwk_file`, `jwks_file`) is read in at run time, as JSON, under the
    same name without the suffix. The files live in the gitignored configs/keys/.
    """
    resolved = _strip_comments(json.loads(json.dumps(plan_config)))  # deep copy

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for key in [k for k in node if isinstance(k, str) and k.endswith("_file")]:
                path = Path(node.pop(key))
                path = path if path.is_absolute() else repo_root / path
                if not path.exists():
                    raise ModuleFailure(
                        f"key file not found at {path}. See the README, 'Per-developer settings', for "
                        "generating the test keys:\n"
                        "  python3 ../conformance-suite/scripts/generate-vp-test-cert.py "
                        "--hostname <your-ngrok-domain> --output configs/keys/vp-signing-jwk.json "
                        "--ca-output configs/keys/vp-test-ca.pem\n"
                        "  python3 scripts/generate-client-jwks.py"
                    )
                node[key[: -len("_file")]] = json.loads(path.read_text())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(resolved)
    return resolved


def run_component(
    suite: ConformanceSuite,
    component: ComponentConfig,
    config: RunnerConfig,
) -> dict[str, Any]:
    """Create the plan, run every module, and return one contract `components[]` entry."""
    plan_config = resolve_plan_config(component.plan_config, config.log_dir.parent)
    plan_config.setdefault("alias", component.alias)
    plan_config.setdefault("description", component.description or f"{component.component} {component.version}")

    log.info("creating plan %s for %s", component.plan_name, component.component)
    plan = suite.create_test_plan(component.plan_name, plan_config, component.variant)
    plan_id = plan["id"]
    log.info("plan %s created: %s/plan-detail.html?plan=%s", plan_id, suite._base.rstrip("/"), plan_id)

    modules_in_plan = plan.get("modules", [])
    if component.only_modules:
        wanted = set(component.only_modules)
        modules_in_plan = [m for m in modules_in_plan if m.get("testModule") in wanted]
        log.info("filtered to %d module(s): %s", len(modules_in_plan), sorted(wanted))

    results: list[dict[str, Any]] = []
    for entry in modules_in_plan:
        module_name = entry["testModule"]
        variant = entry.get("variant") or component.variant
        try:
            results.append(_run_module(suite, component, config, plan_id, module_name, variant))
        except (ModuleFailure, SuiteError, VerifyError, CertifyError, HandoffError, TimeoutError) as exc:
            log.error("module %s could not be executed: %s", module_name, exc)
            results.append(_harness_failure_entry(module_name, variant, exc))

    return {
        "component": component.component,
        "role": component.role,
        "version": component.version,
        "endpoint": component.endpoint,
        "plan": {
            "planId": plan_id,
            "planName": component.plan_name,
            "alias": component.alias,
            "specification": component.specification,
            "variant": component.variant,
            "planUrl": f"{suite._base.rstrip('/')}/plan-detail.html?plan={plan_id}",
        },
        "summary": {},
        "modules": results,
    }


def _run_module(
    suite: ConformanceSuite,
    component: ComponentConfig,
    config: RunnerConfig,
    plan_id: str,
    module_name: str,
    variant: dict[str, str],
) -> dict[str, Any]:
    started_wall = time.monotonic()
    started_at = _utc_now()
    handoff_result = None
    verdict = None

    log.info("--- %s", module_name)
    instance = suite.create_test_from_plan(plan_id, module_name, variant)
    module_id = instance["id"]
    log.info("testId=%s", module_id)

    if component.is_verifier:
        # The module must be listening before Verify mints anything: the request
        # expires 300s from issue, so any time spent waiting here is time taken
        # off the delivery budget.
        state = suite.wait_for_state(module_id, WAITING_STATES, timeout=config.module_timeout_seconds)
        if state in TERMINAL_STATES:
            raise ModuleFailure(
                f"{module_name} reached {state} without ever waiting for an "
                "authorization request; nothing was delivered."
            )

        request = component.verifier_request
        # Which Inji Verify API generation the component speaks. It decides the
        # endpoint, the query language and how the SDK's behaviour is reproduced; see
        # runner/verify_client.py. 0.18 is the default only because it was first.
        api_version = request.get("apiVersion", API_0_18)
        query = load_query(api_version, request["uiConfigFile"], request["credential"])
        verify = InjiVerifyClient(component.endpoint)
        try:
            try:
                handoff_result = deliver(
                    suite,
                    verify,
                    module_id,
                    client_id=request.get("clientId", "inji-verify-ui"),
                    presentation_definition=query if api_version == API_0_18 else None,
                    dcql_query=query if api_version == API_1_0 else None,
                    nonce_mode=request.get("nonceMode", "sdk"),
                    api_version=api_version,
                )
            except RequestExpired as exc:
                raise ModuleFailure(str(exc)) from exc
            final_state = suite.wait_for_state(
                module_id, TERMINAL_STATES, timeout=config.module_timeout_seconds
            )
            # The verdict exists only on the verifier side; fetch it while this client
            # still holds the session. 1.0 only -- 0.18 has no session-results endpoint.
            if api_version == API_1_0:
                verdict = verify.get_vp_session_results(handoff_result.session_cookie)
        finally:
            verify.close()
    elif component.is_issuer:
        final_state, handoff_result = _run_issuer_handoffs(suite, component, config, module_name, module_id)
    else:
        final_state = suite.wait_for_state(
            module_id, TERMINAL_STATES, timeout=config.module_timeout_seconds
        )
    info = suite.get_module_info(module_id)
    result = info.get("result")
    log.info("%s -> %s / %s", module_name, final_state, result)

    raw_log = suite.get_test_log(module_id)
    log_path = _archive_log(config.log_dir, module_name, module_id, raw_log)

    module = normalise.normalise_module(
        module_name=module_name,
        module_id=module_id,
        variant=variant,
        status=final_state,
        result=result,
        log=raw_log,
        suite_base_url=suite._base,
        log_file=str(log_path.relative_to(config.log_dir.parent)) if log_path else None,
        started_at=started_at,
        duration_ms=int((time.monotonic() - started_wall) * 1000),
    )
    if handoff_result is not None:
        # Additive contract field: how the request was produced. A result means
        # little without it -- the nonce findings depend entirely on nonceMode.
        module["handoff"] = handoff_result.as_contract()
    if verdict is not None:
        module["verifierVerdict"] = summarise_verdict(verdict)
        module["reviewResolution"] = normalise.resolve_review(module)
    return module


def summarise_verdict(verdict: dict[str, Any]) -> dict[str, Any]:
    """The parts of Verify's verdict worth recording; never the presented credential."""
    body = verdict.get("body") or {}
    summary: dict[str, Any] = {"httpStatus": verdict.get("httpStatus")}
    if "allChecksSuccessful" in body:
        summary["allChecksSuccessful"] = body["allChecksSuccessful"]
        summary["credentialStatuses"] = [
            c.get("verificationStatus") or c.get("status") for c in body.get("credentialResults") or []
        ]
    for key in ("errorCode", "errorMessage", "error"):
        if key in body:
            summary[key] = body[key]
    return summary


# Some issuer modules wait for more than one offer -- one per client in the multiple-client
# test, a fresh one for additional requests. Deliver each time the module asks, up to this.
MAX_OFFERS_PER_MODULE = 4


def _run_issuer_handoffs(
    suite: ConformanceSuite,
    component: ComponentConfig,
    config: RunnerConfig,
    module_name: str,
    module_id: str,
) -> tuple[str, Any]:
    """
    Deliver a fresh pre-authorized offer each time the module waits for one, then wait for
    it to finish. Modules that never wait (metadata tests, authorization_code variants that
    need no offer) go straight to their terminal state.
    """
    request = component.issuer_request
    handoff_result = None
    offers = 0
    with InjiCertifyClient(request.get("endpoint", component.endpoint)) as certify:
        while True:
            state = suite.wait_for_state(
                module_id, WAITING_STATES | TERMINAL_STATES, timeout=config.module_timeout_seconds
            )
            if state in TERMINAL_STATES:
                return state, handoff_result
            exposed = suite.get_exposed(module_id)
            # waitForCredentialOffer() unexposes tx_code_endpoint, so its presence means the
            # module waits for a code; otherwise an exposed offer endpoint means an offer.
            # credential_offer_endpoint stays exposed after use, so it alone proves nothing.
            if "tx_code_endpoint" in exposed:
                tx_code = request.get("txCode")
                if not tx_code:
                    raise ModuleFailure(f"{module_name} waits for a tx_code; set issuerRequest.txCode")
                handoff_result = deliver_tx_code(suite, module_id, tx_code)
            elif "credential_offer_endpoint" in exposed:
                if offers >= MAX_OFFERS_PER_MODULE:
                    raise ModuleFailure(
                        f"{module_name} asked for more than {MAX_OFFERS_PER_MODULE} credential offers"
                    )
                handoff_result = deliver_credential_offer(
                    suite, certify, module_id,
                    credential_configuration_id=request["credentialConfigurationId"],
                    claims=request.get("claims", {}),
                    tx_code=request.get("txCode"),
                )
                offers += 1
            else:
                # Waiting on something the harness does not provide.
                return suite.wait_for_state(
                    module_id, TERMINAL_STATES, timeout=config.module_timeout_seconds
                ), handoff_result
            # The module can still read WAITING for a moment while the suite processes the
            # offer. Delivering again then would hand the suite an offer it is not waiting
            # for. Wait for it to leave WAITING before deciding whether it wants another.
            for _ in range(40):
                if suite.get_module_info(module_id).get("status") != "WAITING":
                    break
                time.sleep(0.5)


def _archive_log(log_dir: Path, module_name: str, module_id: str, raw_log: Any) -> Path | None:
    """
    Archive the log next to the evidence from manual runs.

    Note this writes the JSON we fetched, which has no `.sig`. The signature comes
    only from the suite's own export, so signed evidence for anything we intend to
    report upstream still has to be exported from the suite. See logs/README.md.
    """
    try:
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        target_dir = log_dir / day
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{module_name}-{module_id}.json"
        # The suite echoes the plan configuration -- including the private signing key
        # -- into its log entries. Never write it to disk unredacted. See runner/redact.py.
        path.write_text(json.dumps(redact(raw_log), indent=2))
        return path
    except OSError as exc:
        log.warning("could not archive log for %s: %s", module_id, exc)
        return None


def _harness_failure_entry(module_name: str, variant: dict[str, str], exc: Exception) -> dict[str, Any]:
    """
    A module the harness could not execute.

    Recorded as SKIP rather than FAIL: the component did not fail conformance, we
    failed to ask it. Reporting this as FAIL would blame MOSIP for our own breakage.
    """
    return {
        "moduleName": module_name,
        "testId": None,
        "variant": variant,
        "status": "HARNESS_ERROR",
        "result": None,
        "verdict": "SKIP",
        "expected": None,
        "regression": False,
        "improvement": False,
        "counts": {"success": 0, "failure": 0, "warning": 0, "info": 0},
        "checks": [
            {
                "src": "harness",
                "result": "FAILURE",
                "msg": f"{type(exc).__name__}: {exc}",
                "requirements": [],
                "detail": {},
                "findingRef": None,
            }
        ],
        "startedAt": _utc_now(),
        "durationMs": None,
        "logUrl": None,
        "logFile": None,
        "logSignatureFile": None,
    }


def run(config: RunnerConfig, mode: str) -> dict[str, Any]:
    """Run every configured component and return the full contract document."""
    started_at = _utc_now()
    started_wall = time.monotonic()

    with ConformanceSuite(config.suite) as suite:
        components = [run_component(suite, c, config) for c in config.components]
        suite_base = config.suite.base_url

    baseline = gate.Baseline.load(config.baseline_file)
    gate_result = gate.apply(components, baseline)

    for component in components:
        component["summary"] = normalise.summarise(component["modules"])

    return {
        "schemaVersion": "1.0",
        "run": {
            "runId": f"{mode}-{started_at}",
            "mode": mode,
            "startedAt": started_at,
            "finishedAt": _utc_now(),
            "durationMs": int((time.monotonic() - started_wall) * 1000),
            "harnessVersion": __version__,
            "conformanceSuite": {"baseUrl": suite_base},
        },
        "components": components,
        "gate": gate_result,
    }
