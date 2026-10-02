"""The plan configuration sent to the suite: key resolution and comment stripping."""

from __future__ import annotations

import json

import pytest

from runner.orchestrator import ModuleFailure, resolve_plan_config


def test_signing_key_file_is_read_in_and_the_reference_removed(tmp_path):
    (tmp_path / "k.json").write_text(json.dumps({"kty": "EC", "d": "secret"}))
    out = resolve_plan_config({"credential": {"signing_jwk_file": "k.json"}}, tmp_path)
    assert out["credential"] == {"signing_jwk": {"kty": "EC", "d": "secret"}}


def test_missing_key_explains_how_to_generate_one(tmp_path):
    with pytest.raises(ModuleFailure, match="generate-vp-test-cert.py"):
        resolve_plan_config({"credential": {"signing_jwk_file": "nope.json"}}, tmp_path)


def test_comments_never_reach_the_suite(tmp_path):
    out = resolve_plan_config(
        {"_comment": "x", "browser": [{"comment": "kept", "_comment_y": "dropped"}]}, tmp_path
    )
    assert out == {"browser": [{"comment": "kept"}]}  # 'comment' is the suite's own field


def test_input_is_not_mutated(tmp_path):
    (tmp_path / "k.json").write_text("{}")
    original = {"credential": {"signing_jwk_file": "k.json"}}
    resolve_plan_config(original, tmp_path)
    assert original == {"credential": {"signing_jwk_file": "k.json"}}
