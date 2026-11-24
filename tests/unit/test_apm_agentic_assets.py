"""
Unit tests for scripts/apm_agentic_assets.py
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "scripts"))

import apm_agentic_assets as aaa


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
        block, source = aaa.select_asset_block(
            org["obs"], "agent-suggestions", org_key="obs"
        )
        assert source == "workflow"
        assert block is not None
        assert block["inputs"]["additional-instructions"] == "specific text"

    def test_falls_back_to_common(self) -> None:
        org = _obs_org(
            common={"inputs": {"additional-instructions": "shared"}},
            workflows={"other": {"inputs": {"additional-instructions": "x"}}},
        )
        block, source = aaa.select_asset_block(
            org["obs"], "agent-suggestions", org_key="obs"
        )
        assert source == "common"
        assert block == org["obs"]["common"]

    def test_workflow_empty_block_still_overrides(self) -> None:
        org = _obs_org(
            common={"inputs": {"additional-instructions": "common"}},
            workflows={"agent-suggestions": {}},
        )
        block, source = aaa.select_asset_block(
            org["obs"], "agent-suggestions", org_key="obs"
        )
        assert source == "workflow"
        assert block == {}

    def test_inner_workflow_overrides_parent(self) -> None:
        org = _obs_org(
            common={"inputs": {"additional-instructions": "common"}},
            workflows={
                "security": {
                    "inputs": {"additional-instructions": "parent"},
                    "inner-workflows": {
                        "obs-aw-security-fixer.yml": {
                            "inputs": {"additional-instructions": "fixer-only"}
                        }
                    },
                }
            },
        )
        block, source = aaa.select_asset_block(
            org["obs"],
            "security",
            org_key="obs",
            workflow_basename="obs-aw-security-fixer.yml",
        )
        assert source == "inner-workflow"
        assert block is not None
        assert block["inputs"]["additional-instructions"] == "fixer-only"

    def test_missing_inner_falls_back_to_workflow_parent(self) -> None:
        org = _obs_org(
            common={"inputs": {"additional-instructions": "common"}},
            workflows={
                "security": {
                    "inputs": {"additional-instructions": "parent"},
                    "inner-workflows": {
                        "obs-aw-security-fixer.yml": {
                            "inputs": {"additional-instructions": "fixer-only"}
                        }
                    },
                }
            },
        )
        block, source = aaa.select_asset_block(
            org["obs"],
            "security",
            org_key="obs",
            workflow_basename="obs-aw-security-triage.yml",
        )
        assert source == "workflow"
        assert block is not None
        assert block["inputs"]["additional-instructions"] == "parent"


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


class TestExtractSetupCommands:
    def test_inline_string(self) -> None:
        assert aaa.extract_setup_commands(
            {"setup-commands": "npm ci"},
            repo_root=pathlib.Path("/tmp"),
        ) == ["npm ci"]

    def test_multiline_block_string(self) -> None:
        block = {
            "setup-commands": "export FOO=1\n\n# skipped\n./scripts/run.sh\n",
        }
        assert aaa.extract_setup_commands(block, repo_root=pathlib.Path("/tmp")) == [
            "export FOO=1",
            "./scripts/run.sh",
        ]

    def test_setup_commands_file(self, repo: pathlib.Path) -> None:
        scripts = repo / "scripts"
        scripts.mkdir()
        (scripts / "setup.txt").write_text(
            "echo from-file\n\n# comment\n./scripts/extra.sh\n",
            encoding="utf-8",
        )
        assert aaa.extract_setup_commands(
            {
                "setup-commands": ["echo inline"],
                "setup-commands-file": "scripts/setup.txt",
            },
            repo_root=repo,
        ) == ["echo inline", "echo from-file", "./scripts/extra.sh"]


class TestResolveApmAssets:
    def test_no_manifest_platform_only(self, repo: pathlib.Path) -> None:
        out = aaa.resolve_apm_assets(
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
        out = aaa.resolve_apm_assets(
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
        out = aaa.resolve_apm_assets(
            repo_root=repo,
            workflow_id="agent-suggestions",
            org_key="obs",
            platform_additional_instructions="",
        )
        assert out["asset_source"] == "workflow"
        assert out["setup_commands"] == ["echo specific"]
        assert "common-only" not in out["additional_instructions"]
        assert "specific-only" in out["additional_instructions"]

    def test_multiline_inline_setup_commands(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common:
      setup-commands: |
        export REPO_BOOTSTRAP=1
        ./scripts/bootstrap.sh
      inputs:
        additional-instructions: bootstrapped
""",
            encoding="utf-8",
        )
        out = aaa.resolve_apm_assets(
            repo_root=repo,
            workflow_id="autodoc",
            org_key="obs",
        )
        assert out["setup_commands"] == [
            "export REPO_BOOTSTRAP=1",
            "./scripts/bootstrap.sh",
        ]

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
        out = aaa.resolve_apm_assets(
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
        out = aaa.resolve_apm_assets(
            repo_root=repo,
            workflow_id="autodoc",
            org_key="obs",
            platform_inputs={"lookback-window": "1 day ago"},
        )
        assert out["inputs"]["lookback-window"] == "3 days ago"

    def test_model_override_from_apm_common(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common:
      inputs:
        model: gpt-4.1
""",
            encoding="utf-8",
        )
        out = aaa.resolve_apm_assets(
            repo_root=repo,
            workflow_id="autodoc",
            org_key="obs",
        )
        assert out["inputs"]["model"] == "gpt-4.1"

    def test_model_omitted_leaves_inputs_without_key(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common:
      inputs:
        lookback-window: 1 day ago
""",
            encoding="utf-8",
        )
        out = aaa.resolve_apm_assets(
            repo_root=repo,
            workflow_id="autodoc",
            org_key="obs",
        )
        assert "model" not in out["inputs"]

    def test_empty_model_fails_closed(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common:
      inputs:
        model: "   "
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="inputs.model must be a non-empty string"):
            aaa.resolve_apm_assets(
                repo_root=repo,
                workflow_id="autodoc",
                org_key="obs",
            )

    def test_non_string_model_fails_closed(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common:
      inputs:
        model: 12
""",
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="inputs.model must be a non-empty string"):
            aaa.resolve_apm_assets(
                repo_root=repo,
                workflow_id="autodoc",
                org_key="obs",
            )

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
        obs_out = aaa.resolve_apm_assets(
            repo_root=repo,
            workflow_id="agent-suggestions",
            org_key="obs",
        )
        docs_out = aaa.resolve_apm_assets(
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
        out = aaa.resolve_apm_assets(
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
            aaa.resolve_apm_assets(
                repo_root=repo,
                workflow_id="agent-suggestions",
                org_key="obs",
            )

    def test_consumer_fragments_before_inline(self, repo: pathlib.Path) -> None:
        frag_dir = repo / ".github" / "ai" / "fragments"
        frag_dir.mkdir(parents=True)
        (frag_dir / "repo-conventions.md").write_text(
            "fragment body\n", encoding="utf-8"
        )
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    fragments:
      repo-conventions: .github/ai/fragments/repo-conventions.md
    common:
      additional-instructions-fragments:
        - repo-conventions
      inputs:
        additional-instructions: |
          inline tail
""",
            encoding="utf-8",
        )
        out = aaa.resolve_apm_assets(
            repo_root=repo,
            workflow_id="autodoc",
            org_key="obs",
            platform_additional_instructions="platform head",
        )
        text = out["additional_instructions"]
        assert text.index("platform head") < text.index("fragment body")
        assert text.index("fragment body") < text.index("inline tail")
        consumer_layers = {layer["layer"]: layer for layer in out["instruction_layers"]}
        assert consumer_layers["consumer-fragments"]["ids"] == ["repo-conventions"]
        assert consumer_layers["consumer-inline"]["present"] is True

    def test_inner_workflow_resolve_apm(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common:
      inputs:
        additional-instructions: common
    workflows:
      security:
        inputs:
          additional-instructions: parent-security
        inner-workflows:
          obs-aw-security-fixer.yml:
            inputs:
              additional-instructions: fixer-only
""",
            encoding="utf-8",
        )
        fixer = aaa.resolve_apm_assets(
            repo_root=repo,
            workflow_id="security",
            org_key="obs",
            workflow_basename="obs-aw-security-fixer.yml",
        )
        triage = aaa.resolve_apm_assets(
            repo_root=repo,
            workflow_id="security",
            org_key="obs",
            workflow_basename="obs-aw-security-triage.yml",
        )
        assert fixer["asset_source"] == "inner-workflow"
        assert "fixer-only" in fixer["additional_instructions"]
        assert "parent-security" not in fixer["additional_instructions"]
        assert triage["asset_source"] == "workflow"
        assert "parent-security" in triage["additional_instructions"]


class TestLoadRegistryWorkflowIds:
    def test_include_common_ids_are_known(self, tmp_path: pathlib.Path) -> None:
        config = tmp_path / "config"
        common = config / "common"
        common.mkdir(parents=True)
        (common / "services.json").write_text(
            '{"services":[{"id":"dependency-review","inner_workflows":'
            '["obs-aw-dependency-review.yml"]}]}',
            encoding="utf-8",
        )
        obs = config / "obs"
        obs.mkdir()
        (obs / "workflow-registry.json").write_text(
            '{"include_common":["dependency-review"],"workflows":'
            '[{"id":"autodoc","inner_workflows":["obs-aw-autodoc.yml"]}]}',
            encoding="utf-8",
        )
        (obs / "active-repositories.json").write_text(
            '{"repositories":[]}', encoding="utf-8"
        )
        aaa.KNOWN_REGISTRY_IDS = None
        known = aaa.load_registry_workflow_ids(config, "obs")
        assert "dependency-review" in known
        assert "autodoc" in known
        aaa.validate_workflow_id("dependency-review", "obs", config_dir=config)

    def test_checked_in_obs_include_common_ids(self) -> None:
        aaa.KNOWN_REGISTRY_IDS = None
        config = _root / "config"
        known = aaa.load_registry_workflow_ids(config, "obs")
        assert "automerge" in known
        assert "dependency-review" in known
        aaa.validate_workflow_id("automerge", "obs", config_dir=config)
        aaa.validate_workflow_id("dependency-review", "obs", config_dir=config)

    def test_default_automerge_policy_when_apm_missing(
        self, repo: pathlib.Path
    ) -> None:
        policy = aaa.resolve_automerge_policy(repo_root=repo, org_key="obs")
        assert policy == aaa.default_automerge_policy()
        assert aaa.MERGE_READY_LABEL in policy["trigger-labels"]

    def test_resolve_automerge_policy_from_apm(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common: {}
    workflows:
      automerge:
        policy:
          trigger-labels:
            - nightshift:risk-low
          forks:
            mode: author-association
            author-associations:
              - MEMBER
              - OWNER
          authors:
            mode: author-association
            author-associations:
              - MEMBER
              - OWNER
          paths:
            allow:
              - docs/**
            deny:
              - "**/*.go"
""",
            encoding="utf-8",
        )
        policy = aaa.resolve_automerge_policy(repo_root=repo, org_key="obs")
        assert policy["trigger-labels"] == [
            aaa.MERGE_READY_LABEL,
            "nightshift:risk-low",
        ]
        assert policy["forks"]["mode"] == "author-association"
        assert policy["authors"]["mode"] == "author-association"
        assert policy["paths"] == {
            "allow": ["docs/**"],
            "deny": ["**/*.go"],
        }
        assert policy["allowed-days-of-week"] == []
        text = aaa.format_automerge_policy_instructions(policy)
        assert "Effective Automerge Policy" in text
        assert "nightshift:risk-low" in text
        assert "docs/**" in text
        assert "**/*.go" in text
        assert "all UTC weekdays" in text
        assert "Do **not** withhold approval" in text
        assert "merge-only" in text

    def test_normalize_automerge_policy_paths_fail_closed(self) -> None:
        with pytest.raises(TypeError, match="paths must be a mapping"):
            aaa.normalize_automerge_policy({"paths": "docs/**"})
        with pytest.raises(TypeError, match="paths.allow must be an array"):
            aaa.normalize_automerge_policy({"paths": {"allow": "docs/**"}})
        with pytest.raises(TypeError, match="paths.deny entries must be strings"):
            aaa.normalize_automerge_policy({"paths": {"deny": [1]}})
        with pytest.raises(ValueError, match="unknown key"):
            aaa.normalize_automerge_policy({"paths": {"alow": ["docs/**"]}})
        with pytest.raises(ValueError, match="non-empty"):
            aaa.normalize_automerge_policy({"paths": {"allow": [""]}})
        with pytest.raises(ValueError, match="unsupported glob"):
            aaa.normalize_automerge_policy({"paths": {"deny": ["helm/values-?.yaml"]}})

    def test_default_dependency_review_policy_when_apm_missing(
        self, repo: pathlib.Path
    ) -> None:
        policy = aaa.resolve_dependency_review_policy(repo_root=repo, org_key="obs")
        assert policy == aaa.default_dependency_review_policy()
        assert policy["max-merge-ready-risk"] == aaa.DEFAULT_MAX_MERGE_READY_RISK

    def test_resolve_automerge_policy_allowed_days(self, repo: pathlib.Path) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common: {}
    workflows:
      automerge:
        policy:
          allowed-days-of-week:
            - Monday
            - tuesday
            - monday
""",
            encoding="utf-8",
        )
        policy = aaa.resolve_automerge_policy(repo_root=repo, org_key="obs")
        assert policy["allowed-days-of-week"] == ["monday", "tuesday"]
        text = aaa.format_automerge_policy_instructions(policy)
        assert "`monday`" in text
        assert "`tuesday`" in text
        assert "all UTC weekdays" not in text
        assert "Do **not** withhold approval" in text

    def test_normalize_automerge_policy_rejects_unknown_weekday(self) -> None:
        with pytest.raises(ValueError, match="unknown weekday"):
            aaa.normalize_automerge_policy({"allowed-days-of-week": ["monady"]})

    def test_resolve_dependency_review_policy_from_apm(
        self, repo: pathlib.Path
    ) -> None:
        (repo / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common: {}
    workflows:
      dependency-review:
        policy:
          max-merge-ready-risk: moderate
""",
            encoding="utf-8",
        )
        policy = aaa.resolve_dependency_review_policy(repo_root=repo, org_key="obs")
        assert policy["max-merge-ready-risk"] == "moderate"
        text = aaa.format_dependency_review_policy_instructions(policy)
        assert "Effective Dependency Review Policy" in text
        assert "`moderate`" in text
        for level in aaa.MERGE_READY_RISK_LEVELS:
            assert f"`{level}`" in text
        assert "`high`" in text

    def test_normalize_dependency_review_policy_rejects_high(
        self,
    ) -> None:
        policy = aaa.normalize_dependency_review_policy(
            {"max-merge-ready-risk": "high"}
        )
        assert policy["max-merge-ready-risk"] == aaa.DEFAULT_MAX_MERGE_READY_RISK

    def test_normalize_dependency_review_policy_accepts_low(self) -> None:
        policy = aaa.normalize_dependency_review_policy({"max-merge-ready-risk": "low"})
        assert policy["max-merge-ready-risk"] == "low"

    def test_dependency_review_policy_uses_checkout_root_not_sibling_head(
        self, tmp_path: pathlib.Path
    ) -> None:
        """
        Restrictive base ceiling must win when resolve reads that checkout.

        Mirrors the wrapper consumer-ref=base.sha contract: a head apm.yml that
        raises max-merge-ready-risk must not affect policy resolved from base.
        """
        base = tmp_path / "base"
        head = tmp_path / "head"
        base.mkdir()
        head.mkdir()
        (base / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common: {}
    workflows:
      dependency-review:
        policy:
          max-merge-ready-risk: low
""",
            encoding="utf-8",
        )
        (head / "apm.yml").write_text(
            """
x-oblt-aw:
  version: 1
  obs:
    common: {}
    workflows:
      dependency-review:
        policy:
          max-merge-ready-risk: moderate
""",
            encoding="utf-8",
        )
        from_base = aaa.resolve_dependency_review_policy(repo_root=base, org_key="obs")
        from_head = aaa.resolve_dependency_review_policy(repo_root=head, org_key="obs")
        assert from_base["max-merge-ready-risk"] == "low"
        assert from_head["max-merge-ready-risk"] == "moderate"
        # Effective policy for the agent must follow the checkout root in use.
        text = aaa.format_dependency_review_policy_instructions(from_base)
        assert "**max-merge-ready-risk**: `low`" in text
        assert "**max-merge-ready-risk**: `moderate`" not in text
