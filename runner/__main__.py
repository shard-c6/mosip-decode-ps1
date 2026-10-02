"""
Command-line entry point.

    python -m runner --component verify
    python -m runner --component certify
    python -m runner --combined

run-conformance.sh is a thin wrapper over this, because the problem statement asks
for that entry point by name.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from . import __version__, config as config_module, gate
from .orchestrator import run
from .redact import redact

DEFAULT_CONFIG = config_module.REPO_ROOT / "configs" / "runner.json"

COMPONENT_ALIASES = {
    "verify": "inji-verify",
    "certify": "inji-certify",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m runner",
        description="Drive the OpenID Foundation conformance suite against the Inji stack.",
    )
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument(
        "--component",
        choices=sorted(COMPONENT_ALIASES),
        help="run one component's plan",
    )
    selection.add_argument(
        "--combined",
        action="store_true",
        help="run every configured component and produce one consolidated report",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="runner configuration file")
    parser.add_argument("--output", type=Path, help="write the contract JSON here (default: stdout)")
    parser.add_argument(
        "--policy",
        choices=[gate.POLICY_REGRESSION, gate.POLICY_ABSOLUTE],
        default=gate.POLICY_REGRESSION,
        help="benchmark policy (see docs/CONTRACT.md and Q4)",
    )
    parser.add_argument(
        "--no-gate-exit",
        action="store_true",
        help="always exit 0, even on a regression. For exploratory runs, never for CI.",
    )
    parser.add_argument("--only", nargs="+", metavar="MODULE", help="run only these modules")
    parser.add_argument(
        "--nonce-mode",
        choices=["sdk", "service"],
        help="override where verifier nonces come from: 'sdk' reproduces what the shipped UI "
        "sends, 'service' lets verify-service generate its own (see runner/verify_client.py)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)-7s %(message)s",
        stream=sys.stderr,
    )

    if not args.config.exists():
        print(f"configuration file not found: {args.config}", file=sys.stderr)
        return 2

    wanted = None if args.combined else [COMPONENT_ALIASES[args.component]]
    mode = "combined" if args.combined else args.component

    try:
        cfg = config_module.load(args.config, wanted)
    except (ValueError, KeyError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    if args.only:
        cfg = _restrict_modules(cfg, args.only)
    if args.nonce_mode:
        cfg = _override_nonce_mode(cfg, args.nonce_mode)

    document = run(cfg, mode)

    payload = json.dumps(redact(document), indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n")
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(payload)

    print("", file=sys.stderr)
    print(gate.summarise_for_humans(document["gate"]), file=sys.stderr)

    if args.no_gate_exit:
        return 0
    return 0 if document["gate"]["passed"] else 1


def _restrict_modules(cfg: config_module.RunnerConfig, only: list[str]) -> config_module.RunnerConfig:
    import dataclasses

    return dataclasses.replace(
        cfg,
        components=[dataclasses.replace(c, only_modules=list(only)) for c in cfg.components],
    )


def _override_nonce_mode(cfg: config_module.RunnerConfig, mode: str) -> config_module.RunnerConfig:
    import dataclasses

    return dataclasses.replace(
        cfg,
        components=[
            dataclasses.replace(c, verifier_request={**c.verifier_request, "nonceMode": mode})
            if c.is_verifier else c
            for c in cfg.components
        ],
    )


if __name__ == "__main__":
    sys.exit(main())
