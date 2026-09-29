"""
Configuration loading.

Everything that could change when the answer to Q1 arrives -- which specification
version we benchmark against -- lives here as data rather than code. Switching
between the OID4VP 1.0 Final plan and the ID2 draft plan is a config edit, not a
rewrite. See docs/PLAN.md, "Design decision that de-risks Q1".
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PLAN_DIR = REPO_ROOT / "configs" / "plans"


@dataclass(frozen=True)
class SuiteConfig:
    """How to reach the conformance suite."""

    base_url: str = "https://localhost.emobix.co.uk:8443"
    # The suite's local dev profile serves a self-signed certificate for a hostname
    # that resolves to 127.0.0.1. Verification is off for that reason alone; it must
    # stay on for any non-local deployment.
    verify_ssl: bool = False
    # The local dev profile needs no token; a hosted deployment does.
    api_token: str | None = None
    timeout_seconds: int = 30


@dataclass(frozen=True)
class ComponentConfig:
    """A MOSIP component under test and the plan to run against it."""

    component: str                   # "inji-verify" | "inji-certify"
    role: str                        # "verifier" | "issuer"
    version: str
    endpoint: str                    # the same env.endpoint the testrig targets
    plan_name: str
    specification: str
    variant: dict[str, str]
    alias: str
    description: str = ""
    # Passed through to the suite as the test plan configuration. Carries the
    # 'browser' automation block that fills the screenshot placeholder, among others.
    plan_config: dict[str, Any] = field(default_factory=dict)
    # Modules to run. Empty means every module the plan returns.
    only_modules: list[str] = field(default_factory=list)
    # Verifier components only: how to ask the component for an authorization request.
    # Kept separate from plan_config, which is sent to the conformance suite -- these
    # values are for Inji Verify, and mixing the two would leak them into the suite.
    verifier_request: dict[str, Any] = field(default_factory=dict)

    @property
    def is_verifier(self) -> bool:
        return self.role == "verifier"


@dataclass(frozen=True)
class RunnerConfig:
    suite: SuiteConfig
    components: list[ComponentConfig]
    baseline_file: Path
    log_dir: Path
    # How long to wait for a module to reach a terminal state.
    module_timeout_seconds: int = 300


def _component_from_dict(raw: dict[str, Any]) -> ComponentConfig:
    return ComponentConfig(
        component=raw["component"],
        role=raw["role"],
        version=raw.get("version", "unknown"),
        endpoint=raw["endpoint"],
        plan_name=raw["planName"],
        specification=raw.get("specification", raw["planName"]),
        variant=raw.get("variant", {}),
        alias=raw.get("alias", raw["component"]),
        description=raw.get("description", ""),
        plan_config=raw.get("planConfig", {}),
        only_modules=raw.get("onlyModules", []),
        verifier_request=_resolve_request_paths(raw.get("verifierRequest", {})),
    )


def _resolve_request_paths(request: dict[str, Any]) -> dict[str, Any]:
    request = dict(request)
    if "uiConfigFile" in request:
        request["uiConfigFile"] = str(_resolve(request["uiConfigFile"]))
    return request


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _apply_local_overrides(raw: dict[str, Any], config_path: Path) -> dict[str, Any]:
    """
    Merge `<name>.local.json` over the committed config, if present.

    Each developer's ngrok hostname differs and must not be committed, so the
    shared file carries one default and a gitignored local file overrides it.
    Components are matched by their `component` name; top-level keys merge deeply.
    """
    local_path = config_path.with_name(config_path.stem + ".local.json")
    if not local_path.exists():
        return raw
    local = json.loads(local_path.read_text())

    merged = _deep_merge({k: v for k, v in raw.items() if k != "components"},
                         {k: v for k, v in local.items() if k != "components"})
    overrides = {c["component"]: c for c in local.get("components", [])}
    merged["components"] = [
        _deep_merge(c, overrides.get(c["component"], {})) for c in raw["components"]
    ]
    return merged


def load(path: Path | str, components: list[str] | None = None) -> RunnerConfig:
    """
    Load a runner configuration file.

    `components` filters to a subset by name, which is what --component does.
    """
    path = Path(path)
    raw = _apply_local_overrides(json.loads(path.read_text()), path)

    suite_raw = raw.get("suite", {})
    suite = SuiteConfig(
        base_url=suite_raw.get("baseUrl", SuiteConfig.base_url),
        verify_ssl=suite_raw.get("verifySsl", SuiteConfig.verify_ssl),
        api_token=suite_raw.get("apiToken"),
        timeout_seconds=suite_raw.get("timeoutSeconds", SuiteConfig.timeout_seconds),
    )

    all_components = [_component_from_dict(c) for c in raw["components"]]
    if components:
        wanted = set(components)
        selected = [c for c in all_components if c.component in wanted]
        missing = wanted - {c.component for c in selected}
        if missing:
            known = ", ".join(sorted(c.component for c in all_components))
            raise ValueError(
                f"no configuration for component(s) {sorted(missing)}; "
                f"this file defines: {known}"
            )
    else:
        selected = all_components

    return RunnerConfig(
        suite=suite,
        components=selected,
        baseline_file=_resolve(raw.get("baselineFile", "configs/contract/expected-failures.json")),
        log_dir=_resolve(raw.get("logDir", "logs")),
        module_timeout_seconds=raw.get("moduleTimeoutSeconds", 300),
    )


def _resolve(p: str) -> Path:
    """Config paths are repo-relative so a config file is portable between machines."""
    path = Path(p)
    return path if path.is_absolute() else REPO_ROOT / path
