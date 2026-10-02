"""
Remove private key material before anything is written to disk.

The conformance suite echoes the plan configuration into every log entry, and since
2 October that configuration carries `credential.signing_jwk` -- a private key. The
first archived logs of that day contained it, and were caught before they were
committed. Everything the runner writes now passes through here.

A JWK's private members are defined in RFC 7518 section 6: d, p, q, dp, dq, qi (EC
and RSA) and k (symmetric). Only objects that look like a JWK -- they carry "kty" --
are touched, so an unrelated field that happens to be called "d" survives.
"""

from __future__ import annotations

from typing import Any

PRIVATE_JWK_MEMBERS = frozenset({"d", "p", "q", "dp", "dq", "qi", "k", "oth"})
REDACTED = "<redacted: private key material>"


def redact(value: Any) -> Any:
    """Return a copy of `value` with every JWK's private members replaced."""
    if isinstance(value, dict):
        is_jwk = "kty" in value
        return {
            k: (REDACTED if is_jwk and k in PRIVATE_JWK_MEMBERS else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def find_private_keys(value: Any, path: str = "$") -> list[str]:
    """Paths of any unredacted private JWK members. Empty means safe to publish."""
    found: list[str] = []
    if isinstance(value, dict):
        if "kty" in value:
            found += [f"{path}.{k}" for k in value if k in PRIVATE_JWK_MEMBERS and value[k] != REDACTED]
        for k, v in value.items():
            found += find_private_keys(v, f"{path}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            found += find_private_keys(v, f"{path}[{i}]")
    return found
