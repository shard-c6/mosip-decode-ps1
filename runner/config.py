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
    )


def load(path: Path | str, components: list[str] | None = None) -> RunnerConfig:
    """
    Load a runner configuration file.

    `components` filters to a subset by name, which is what --component does.
    """
    path = Path(path)
    raw = json.loads(path.read_text())

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
