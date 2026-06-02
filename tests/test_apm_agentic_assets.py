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


def _obs_org(
    *,
    common: dict | None = None,
    workflows: dict | None = None,
) -> dict:
    block: dict = {
        "common": common
        if common is not None
        else {"inputs": {"additional-instructions": "obs common"}},
    }
    if workflows is not None:
        block["workflows"] = workflows
    return {"version": 1, "obs": block}


class TestSelectAssetBlock:
    def test_workflow_override_ignores_common(self) -> None:
        org = _obs_org(
            common={"inputs": {"additional-instructions": "common text"}},
            workflows={
                "agent-suggestions": {
                    "inputs": {"additional-instructions": "specific text"}
                }
            },
        )
        block = aaa.select_asset_block(org["obs"], "agent-suggestions", org_key="obs")
        assert block is not None
        assert block["inputs"]["additional-instructions"] == "specific text"

    def test_falls_back_to_common(self) -> None:
        org = _obs_org(
            common={"inputs": {"additional-instructions": "shared"}},
            workflows={"other": {"inputs": {"additional-instructions": "x"}}},
        )
        block = aaa.select_asset_block(org["obs"], "agent-suggestions", org_key="obs")
        assert block == org["obs"]["common"]

    def test_workflow_empty_block_still_overrides(self) -> None:
        org = _obs_org(
            common={"inputs": {"additional-instructions": "common"}},
            workflows={"agent-suggestions": {}},
        )
        block = aaa.select_asset_block(org["obs"], "agent-suggestions", org_key="obs")
        assert block == {}


class TestExtractOrgExtension:
    def test_missing_org_returns_none(self) -> None:
        ext = {"version": 1, "obs": _obs_org()["obs"]}
        assert aaa.extract_org_extension(ext, "docs") is None

    def test_rejects_legacy_flat_layout(self) -> None:
        ext = {
            "version": 1,
            "common": {"inputs": {"additional-instructions": "flat"}},
        }
        with pytest.raises(ValueError, match="nest assets under org keys"):
            aaa.extract_org_extension(ext, "obs")


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
  obs:
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
  obs:
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
  obs:
    common:
      inputs:
        additional-instructions: fallback
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
  obs:
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

    def test_multi_org_isolated_common(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common:
      inputs:
        additional-instructions: obs guidance
  docs:
    common:
      inputs:
        additional-instructions: docs guidance
""",
            encoding="utf-8",
        )
        obs_out = aaa.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="agent-suggestions",
            org_key="obs",
        )
        docs_out = aaa.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="docs-pr-ai-menu",
            org_key="docs",
        )
        assert obs_out["asset_source"] == "common"
        assert "obs guidance" in obs_out["additional_instructions"]
        assert "docs guidance" not in obs_out["additional_instructions"]
        assert docs_out["asset_source"] == "common"
        assert "docs guidance" in docs_out["additional_instructions"]

    def test_missing_org_block_extension_present_no_assets(
        self, repo: pathlib.Path
    ) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common:
      inputs:
        additional-instructions: obs only
""",
            encoding="utf-8",
        )
        out = aaa.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="docs-pr-ai-menu",
            org_key="docs",
            platform_additional_instructions="platform",
        )
        assert out["apm_extension_present"] is True
        assert out["asset_source"] == "none"
        assert out["additional_instructions"] == "platform"
        assert out["setup_commands"] == []

    def test_rejects_legacy_flat_manifest(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  common:
    inputs:
      additional-instructions: legacy
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="nest assets under org keys"):
            aaa.resolve_agentic_assets(
                repo_root=repo,
                workflow_id="agent-suggestions",
                org_key="obs",
            )
