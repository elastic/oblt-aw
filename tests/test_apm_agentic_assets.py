"""
Unit tests for scripts/apm_agentic_assets.py
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root / "scripts"))

import apm_agentic_assets as aaa  # noqa: E402


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path


class TestSelectAssetBlock:
    def test_workflow_override_ignores_common(self, repo: pathlib.Path) -> None:
        ext = {
            "version": 1,
            "common": {"inputs": {"additional-instructions": "common text"}},
            "workflows": {
                "agent-suggestions": {
                    "inputs": {"additional-instructions": "specific text"}
                }
            },
        }
        block = aaa.select_asset_block(ext, "agent-suggestions")
        assert block is not None
        assert block["inputs"]["additional-instructions"] == "specific text"

    def test_falls_back_to_common(self) -> None:
        ext = {
            "common": {"inputs": {"additional-instructions": "shared"}},
            "workflows": {"other": {"inputs": {"additional-instructions": "x"}}},
        }
        block = aaa.select_asset_block(ext, "agent-suggestions")
        assert block == ext["common"]

    def test_workflow_empty_block_still_overrides(self) -> None:
        ext = {
            "common": {"inputs": {"additional-instructions": "common"}},
            "workflows": {"agent-suggestions": {}},
        }
        block = aaa.select_asset_block(ext, "agent-suggestions")
        assert block == {}


class TestResolveAgenticAssets:
    def test_no_manifest_platform_only(self, repo: pathlib.Path) -> None:
        out = aaa.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="agent-suggestions",
            org_key="obs",
            platform_additional_instructions="platform rules",
        )
        assert out["apm_manifest_present"] is False
        assert out["asset_source"] == "none"
        assert out["additional_instructions"] == "platform rules"
        assert out["setup_commands"] == []

    def test_common_assets(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  common:
    setup-commands:
      - echo bootstrap
    inputs:
      additional-instructions: |
        repo-wide guidance
""",
            encoding="utf-8",
        )
        out = aaa.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="issue-triage",
            org_key="obs",
            platform_additional_instructions="cp",
        )
        assert out["asset_source"] == "common"
        assert "cp" in out["additional_instructions"]
        assert "repo-wide guidance" in out["additional_instructions"]
        assert out["setup_commands"] == ["echo bootstrap"]

    def test_workflow_override(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  common:
    setup-commands:
      - echo common
    inputs:
      additional-instructions: common-only
  workflows:
    agent-suggestions:
      setup-commands:
        - echo specific
      inputs:
        additional-instructions: specific-only
""",
            encoding="utf-8",
        )
        out = aaa.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="agent-suggestions",
            org_key="obs",
            platform_additional_instructions="",
        )
        assert out["asset_source"] == "workflow"
        assert out["setup_commands"] == ["echo specific"]
        assert "common-only" not in out["additional_instructions"]
        assert "specific-only" in out["additional_instructions"]

    def test_file_input(self, repo: pathlib.Path) -> None:
        ai_dir = repo / ".github" / "ai"
        ai_dir.mkdir(parents=True)
        (ai_dir / "extra.md").write_text("from file\n", encoding="utf-8")
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  workflows:
    security:
      inputs:
        additional-instructions-file: .github/ai/extra.md
""",
            encoding="utf-8",
        )
        out = aaa.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="security",
            org_key="obs",
        )
        assert "from file" in out["additional_instructions"]

    def test_platform_inputs_overridden_by_apm(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  common:
    inputs:
      lookback-window: 3 days ago
""",
            encoding="utf-8",
        )
        out = aaa.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="autodoc",
            org_key="obs",
            platform_inputs={"lookback-window": "1 day ago"},
        )
        assert out["inputs"]["lookback-window"] == "3 days ago"
