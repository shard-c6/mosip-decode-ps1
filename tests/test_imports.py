"""
Every runner module must import.

Added 29 September after a refactor deleted a class that only handoff.py and
orchestrator.py import. The unit tests passed -- none of them touch those modules --
and the break surfaced only when the CLI was launched against the live stack.
"""

import importlib

import pytest

MODULES = [
    "runner", "runner.config", "runner.suite", "runner.verify_client", "runner.handoff",
    "runner.normalise", "runner.gate", "runner.orchestrator", "runner.__main__",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)
