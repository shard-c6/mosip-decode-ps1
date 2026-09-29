"""Config loading, including the per-developer local override."""

from __future__ import annotations

import json

import pytest

from runner import config


def _write(path, data):
    path.write_text(json.dumps(data))
    return path


BASE = {
    "suite": {"baseUrl": "https://suite.test"},
    "components": [{
        "component": "inji-verify", "role": "verifier", "endpoint": "http://localhost:8080/v1/verify",
        "planName": "p", "variant": {"a": "1"},
        "verifierRequest": {"credential": "Mock Identity (SD JWT)", "nonceMode": "sdk"},
    }],
}


def test_loads_without_a_local_file(tmp_path):
    cfg = config.load(_write(tmp_path / "runner.json", BASE))
    assert cfg.components[0].verifier_request["nonceMode"] == "sdk"


def test_local_file_overrides_by_component_name_and_merges_deeply(tmp_path):
    main = _write(tmp_path / "runner.json", BASE)
    _write(tmp_path / "runner.local.json", {
        "components": [{"component": "inji-verify", "verifierRequest": {"nonceMode": "service"}}]
    })
    c = config.load(main).components[0]
    assert c.verifier_request["nonceMode"] == "service"
    assert c.verifier_request["credential"] == "Mock Identity (SD JWT)"  # untouched key survives
    assert c.variant == {"a": "1"}


def test_selecting_an_unconfigured_component_names_what_exists(tmp_path):
    with pytest.raises(ValueError, match="inji-verify"):
        config.load(_write(tmp_path / "runner.json", BASE), ["inji-certify"])


def test_committed_config_loads():
    cfg = config.load(config.REPO_ROOT / "configs" / "runner.json")
    v = cfg.components[0]
    assert v.is_verifier and v.verifier_request["nonceMode"] in ("sdk", "service")
