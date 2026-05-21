"""Tests for ingress dispatch config in workflow-registry.json."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import common  # noqa: E402


def test_ingress_route_specs_requires_dispatch_list() -> None:
    registry = {
        "workflows": [
            {
                "id": "x",
                "dispatch": {"workflow": "gh-aw-a.yml", "secrets": "copilot"},
            }
        ]
    }
    with pytest.raises(SystemExit, match="dispatch must be a list"):
        common.ingress_route_specs_from_registry(registry)


def test_ingress_route_specs_requires_route_id() -> None:
    registry = {
        "workflows": [
            {
                "id": "x",
                "dispatch": [{"workflow": "gh-aw-a.yml", "secrets": "copilot"}],
            }
        ]
    }
    with pytest.raises(SystemExit, match="dispatch route missing id"):
        common.ingress_route_specs_from_registry(registry)


def test_ingress_route_specs_requires_workflow_and_secrets() -> None:
    registry = {
        "workflows": [
            {
                "id": "x",
                "dispatch": [{"id": "x", "secrets": "copilot"}],
            }
        ]
    }
    with pytest.raises(SystemExit, match="dispatch.workflow"):
        common.ingress_route_specs_from_registry(registry)


def test_load_obs_registry_has_all_ingress_routes() -> None:
    config_dir = pathlib.Path(__file__).parent.parent / "config"
    registry = common.load_workflow_registry(config_dir / "obs")
    specs = common.ingress_route_specs_from_registry(registry)
    assert "agent-suggestions" in specs
    assert "security-triage" in specs
    assert "resource-not-accessible-by-integration-fixer" in specs
    assert len(specs) == 15
