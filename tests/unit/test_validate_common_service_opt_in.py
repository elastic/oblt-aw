"""Tests for scripts/validate_common_service_opt_in.py."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import validate_common_service_opt_in as validator

_ORCH_PR = """\
on:
  workflow_call:
jobs:
  run-aw-prelude:
    uses: ./.github/workflows/aw-prelude.yml
    with:
      control-plane-workflows: '["obs-aw-dependency-review.yml"]'
  dependency-review:
    needs: run-aw-prelude
    uses: ./.github/workflows/obs-aw-dependency-review.yml
"""


def _write_org(
    config_dir: pathlib.Path,
    org_key: str,
    *,
    include_common: list[str] | None = None,
    workflows: list[dict] | None = None,
) -> pathlib.Path:
    org_dir = config_dir / org_key
    org_dir.mkdir(parents=True)
    payload: dict = {"workflows": workflows or []}
    if include_common is not None:
        payload["include_common"] = include_common
    (org_dir / "workflow-registry.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    (org_dir / "active-repositories.json").write_text(
        json.dumps({"repositories": []}), encoding="utf-8"
    )
    return org_dir


def _write_common(config_dir: pathlib.Path) -> None:
    common = config_dir / "common"
    common.mkdir(parents=True)
    (common / "services.json").write_text(
        json.dumps(
            {
                "services": [
                    {
                        "id": "dependency-review",
                        "inner_workflows": ["obs-aw-dependency-review.yml"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )


def test_skips_orgs_without_include_common(tmp_path: pathlib.Path) -> None:
    config = tmp_path / "config"
    _write_common(config)
    _write_org(config, "docs", workflows=[])
    assert (
        validator.validate_org_common_opt_in(
            config / "docs",
            config,
            workflows_dir=tmp_path / "workflows",
            remote_root=tmp_path / "remote",
        )
        == []
    )


def test_fails_when_orchestrator_missing(tmp_path: pathlib.Path) -> None:
    config = tmp_path / "config"
    _write_common(config)
    _write_org(config, "docs", include_common=["dependency-review"])
    errors = validator.validate_org_common_opt_in(
        config / "docs",
        config,
        workflows_dir=tmp_path / "workflows",
        remote_root=tmp_path / "remote",
    )
    assert errors
    assert any("no docs-aw-event-" in err for err in errors)


def test_fails_when_trigger_missing(tmp_path: pathlib.Path) -> None:
    config = tmp_path / "config"
    workflows = tmp_path / "workflows"
    remote = tmp_path / "remote"
    _write_common(config)
    _write_org(config, "docs", include_common=["dependency-review"])
    workflows.mkdir()
    (workflows / "docs-aw-event-pull-request.yml").write_text(
        _ORCH_PR, encoding="utf-8"
    )
    errors = validator.validate_org_common_opt_in(
        config / "docs",
        config,
        workflows_dir=workflows,
        remote_root=remote,
    )
    assert any("trigger-docs-aw-pull-request" in err for err in errors)


def test_passes_when_orchestrator_and_trigger_present(
    tmp_path: pathlib.Path,
) -> None:
    config = tmp_path / "config"
    workflows = tmp_path / "workflows"
    remote = tmp_path / "remote"
    _write_common(config)
    _write_org(config, "docs", include_common=["dependency-review"])
    workflows.mkdir()
    (workflows / "docs-aw-event-pull-request.yml").write_text(
        _ORCH_PR, encoding="utf-8"
    )
    trigger_dir = remote / "docs" / ".github" / "workflows"
    trigger_dir.mkdir(parents=True)
    (trigger_dir / "trigger-docs-aw-pull-request.yml").write_text(
        "name: Docs PR\non:\n  pull_request:\n",
        encoding="utf-8",
    )
    assert (
        validator.validate_org_common_opt_in(
            config / "docs",
            config,
            workflows_dir=workflows,
            remote_root=remote,
        )
        == []
    )


def test_main_passes_on_checked_in_repo() -> None:
    assert validator.main() == 0
