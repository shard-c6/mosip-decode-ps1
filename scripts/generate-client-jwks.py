#!/usr/bin/env python3
"""
Generate the OAuth client key sets the suite's OID4VCI issuer plan needs.

The issuer plan authenticates its emulated wallet to the issuer with private_key_jwt and
binds tokens with DPoP, so `client.jwks` and `client2.jwks` must each hold a private EC
P-256 key. Private key material: written to the gitignored configs/keys/ and referenced
from configs/runner.json as client.jwks_file / client2.jwks_file, never committed.

    python3 scripts/generate-client-jwks.py
"""

import base64
import json
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric import ec

KEYS = Path(__file__).resolve().parent.parent / "configs" / "keys"


def b64url(n: int, length: int = 32) -> str:
    return base64.urlsafe_b64encode(n.to_bytes(length, "big")).rstrip(b"=").decode()


def ec_jwks() -> dict:
    key = ec.generate_private_key(ec.SECP256R1())
    pub = key.public_key().public_numbers()
    return {"keys": [{
        "kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig",
        "kid": secrets.token_urlsafe(12),
        "x": b64url(pub.x), "y": b64url(pub.y), "d": b64url(key.private_numbers().private_value),
    }]}


def main() -> None:
    KEYS.mkdir(parents=True, exist_ok=True)
    for name in ("vci-client-jwks.json", "vci-client2-jwks.json"):
        path = KEYS / name
        if path.exists():
            print(f"exists, kept: {path}")
            continue
        path.write_text(json.dumps(ec_jwks(), indent=2) + "\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
