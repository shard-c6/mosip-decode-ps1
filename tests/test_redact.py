"""
Private key material must never reach the repository.

Added 2 October, after archived logs were found to contain the suite's signing key --
caught before commit. The last test is the important one: it scans everything under
logs/ and configs/contract/, so a regression anywhere in the write path fails CI rather
than leaking a key into a public repository.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runner.redact import REDACTED, find_private_keys, redact

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_private_members_of_a_jwk_are_redacted_and_public_ones_kept():
    jwk = {"kty": "EC", "crv": "P-256", "x": "pub-x", "y": "pub-y", "d": "SECRET", "x5c": ["cert"]}
    out = redact({"config": {"credential": {"signing_jwk": jwk}}})
    key = out["config"]["credential"]["signing_jwk"]
    assert key["d"] == REDACTED
    assert key["x"] == "pub-x" and key["x5c"] == ["cert"]


def test_rsa_and_symmetric_private_members_are_redacted():
    out = redact([{"kty": "RSA", "n": "N", "e": "AQAB", "d": "D", "p": "P", "q": "Q",
                   "dp": "DP", "dq": "DQ", "qi": "QI"}, {"kty": "oct", "k": "K"}])
    assert all(out[0][m] == REDACTED for m in ("d", "p", "q", "dp", "dq", "qi"))
    assert out[0]["n"] == "N" and out[1]["k"] == REDACTED


def test_fields_named_d_outside_a_jwk_are_left_alone():
    assert redact({"d": "not a key", "nested": {"d": 1}}) == {"d": "not a key", "nested": {"d": 1}}


def test_input_is_not_mutated():
    original = {"kty": "EC", "d": "SECRET"}
    redact(original)
    assert original["d"] == "SECRET"


def test_find_private_keys_reports_paths():
    assert find_private_keys({"a": [{"kty": "EC", "d": "S"}]}) == ["$.a[0].d"]
    assert find_private_keys(redact({"a": [{"kty": "EC", "d": "S"}]})) == []


PUBLISHED = sorted(
    [*REPO_ROOT.joinpath("logs").rglob("*.json"), *REPO_ROOT.joinpath("configs", "contract").glob("*.json")]
)


@pytest.mark.parametrize("path", PUBLISHED, ids=lambda p: str(p.relative_to(REPO_ROOT)))
def test_no_committed_file_contains_private_key_material(path):
    leaks = find_private_keys(json.loads(path.read_text()))
    assert not leaks, f"private key material in {path}: {leaks}"
