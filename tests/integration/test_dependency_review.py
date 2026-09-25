"""
Integration checks for obs:dependency-review.

Proves wrapper ↔ aw-resolve-agentic-assets ↔ lock input wiring using frozen
consumer fixtures. Does not invoke a live model or mint tokens.
"""

from __future__ import annotations

import json
import pathlib
import sys

import yaml

_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "scripts"))

import agentic_assets_resolver as resolver

WRAPPER_BASENAME = "obs-aw-dependency-review.yml"
LOCK_BASENAME = "gh-aw-dependency-review.lock.yml"
WORKFLOW_ID = "dependency-review"
ORG_KEY = "obs"
RESOLVE_JOB = "resolve-apm-assets"
AGENT_JOB = "dependency-review"

FIXTURE_ROOT = _root / "testdata" / "agentic" / "dependency-review"
CONSUMER_ROOT = FIXTURE_ROOT / "consumer"
EXPECTED_SETUP = FIXTURE_ROOT / "expected" / "setup-commands.json"
EXPECTED_LAYERS = FIXTURE_ROOT / "expected" / "instruction-layers.json"
WRAPPER_PATH = _root / ".github" / "workflows" / WRAPPER_BASENAME
LOCK_PATH = _root / ".github" / "workflows" / LOCK_BASENAME


def _load_yaml(path: pathlib.Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path}: expected mapping root"
    return data


def _workflow_on_block(workflow: dict) -> dict:
    """Return the ``on`` mapping; PyYAML 1.1 may parse the key ``on`` as ``True``."""
    on_block = workflow.get("on")
    if on_block is None:
        on_block = workflow.get(True)
    assert isinstance(on_block, dict), "workflow missing on: mapping"
    return on_block


def _lock_workflow_call_inputs(lock: dict) -> dict:
    workflow_call = _workflow_on_block(lock).get("workflow_call") or {}
    inputs = workflow_call.get("inputs") or {}
    assert isinstance(inputs, dict), f"{LOCK_BASENAME}: missing workflow_call.inputs"
    return inputs


class TestDependencyReviewWrapperLockWiring:
    """Static contract: wrapper maps resolve outputs onto lock inputs."""

    def test_resolve_job_targets_wrapper_basename(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        resolve_job = wrapper["jobs"][RESOLVE_JOB]
        assert resolve_job["uses"].endswith("aw-resolve-agentic-assets.yml"), (
            f"unexpected resolve uses: {resolve_job['uses']!r}"
        )
        assert resolve_job["with"]["workflow-basename"] == WRAPPER_BASENAME
        assert "platform-additional-instructions" not in (resolve_job.get("with") or {})

    def test_agent_job_passes_resolve_outputs_to_lock_inputs(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        lock = _load_yaml(LOCK_PATH)
        agent = wrapper["jobs"][AGENT_JOB]
        with_block = agent.get("with") or {}

        uses = agent["uses"]
        assert isinstance(uses, str)
        assert uses.startswith("elastic/oblt-aw/.github/workflows/"), (
            f"{AGENT_JOB} must call in-repo lock under elastic/oblt-aw "
            f"(got {uses!r}; rollback to elastic/ai-github-actions must fail)"
        )
        assert LOCK_BASENAME in uses, f"{AGENT_JOB} must call in-repo {LOCK_BASENAME}"
        needs = agent.get("needs") or []
        if isinstance(needs, str):
            needs = [needs]
        assert RESOLVE_JOB in needs, (
            f"{AGENT_JOB} must need {RESOLVE_JOB} so needs.*.outputs resolve at runtime"
        )
        assert (
            with_block.get("additional-instructions")
            == "${{ needs.resolve-apm-assets.outputs.resolved-additional-instructions }}"
        )
        assert (
            with_block.get("setup-commands")
            == "${{ join(fromJSON(needs.resolve-apm-assets.outputs."
            "resolved-setup-commands-json), fromJSON('\"\\n\"')) }}"
        )
        assert (
            with_block.get("github-token-policy") == "${{ inputs.shared-token-policy }}"
        )
        assert "allowed-bot-users" not in with_block
        assert "classification-labels" not in with_block
        assert "report-failure-as-issue" not in with_block

        lock_inputs = _lock_workflow_call_inputs(lock)
        for key in (
            "additional-instructions",
            "setup-commands",
            "github-token-policy",
        ):
            assert key in lock_inputs, (
                f"{LOCK_BASENAME} must declare workflow_call input {key!r}"
            )
        assert "classification-labels" not in lock_inputs, (
            f"{LOCK_BASENAME} must hardcode the merge-ready allowlist "
            "(no caller-overridable classification-labels input)"
        )
        for dropped in (
            "model",
            "allowed-bot-users",
            "messages-footer",
            "report-failure-as-issue",
            "classification-labels",
        ):
            assert dropped not in lock_inputs, (
                f"{LOCK_BASENAME} must not expose simplified-away input {dropped!r}"
            )

    def test_wrapper_workflow_call_inputs_are_slim(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        inputs = (
            _workflow_on_block(wrapper).get("workflow_call", {}).get("inputs") or {}
        )
        assert set(inputs) == {"shared-proceed", "shared-token-policy"}

    def test_wrapper_does_not_invoke_agent_engine_inline(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        agent = wrapper["jobs"][AGENT_JOB]
        assert "uses" in agent
        assert "steps" not in agent


class TestDependencyReviewResolveFixtures:
    """Resolve against frozen consumer fixtures (no live model / tokens)."""

    def test_resolve_maps_additional_instructions_setup_and_layers(self) -> None:
        expected_setup = json.loads(EXPECTED_SETUP.read_text(encoding="utf-8"))
        expected_layers = json.loads(EXPECTED_LAYERS.read_text(encoding="utf-8"))

        resolved = resolver.resolve_agentic_assets(
            repo_root=CONSUMER_ROOT,
            workflow_id=WORKFLOW_ID,
            org_key=ORG_KEY,
            platform_additional_instructions="",
            config_dir=_root / "config",
            workflow_basename=WRAPPER_BASENAME,
        )

        assert resolved["asset_source"] == "workflow"
        assert resolved["setup_commands"] == expected_setup

        text = resolved["additional_instructions"]
        assert "DR_CONSUMER_FRAGMENT_MARKER" in text
        assert "DR_CONSUMER_INLINE_MARKER" in text
        assert "DR_COMMON_INLINE_SHOULD_NOT_APPLY" not in text
        assert text.index("DR_CONSUMER_FRAGMENT_MARKER") < text.index(
            "DR_CONSUMER_INLINE_MARKER"
        )

        layers = resolved["instruction_layers"]
        assert layers["org-key"] == expected_layers["org-key"]
        assert layers["workflow-id"] == expected_layers["workflow-id"]
        assert layers["workflow-basename"] == expected_layers["workflow-basename"]
        assert layers["layers"] == expected_layers["layers"]

    def test_resolve_without_apm_is_empty_without_platform(
        self, tmp_path: pathlib.Path
    ) -> None:
        resolved = resolver.resolve_agentic_assets(
            repo_root=tmp_path,
            workflow_id=WORKFLOW_ID,
            org_key=ORG_KEY,
            platform_additional_instructions="",
            config_dir=_root / "config",
            workflow_basename=WRAPPER_BASENAME,
        )

        assert resolved["apm_manifest_present"] is False
        assert resolved["setup_commands"] == []
        assert resolved["additional_instructions"].strip() == ""
        by_name = {
            layer["layer"]: layer for layer in resolved["instruction_layers"]["layers"]
        }
        assert by_name["platform-inline"]["present"] is False
        assert by_name["consumer-inline"]["present"] is False
        assert by_name["control-plane-workflow"]["ids"] == []


def test_fixture_tree_is_present() -> None:
    assert (CONSUMER_ROOT / "apm.yml").is_file()
    assert EXPECTED_SETUP.is_file()
    assert EXPECTED_LAYERS.is_file()
    assert LOCK_PATH.is_file()
    assert (FIXTURE_ROOT / "cases" / "actions-pin-bump-live" / "case.json").is_file()


def test_hardcoded_bots_match_allowed_pr_authors() -> None:
    """Lock on.bots / trusted-users must stay aligned with allowed_pr_authors.json."""
    import re

    source = (_root / ".github" / "workflows" / "gh-aw-dependency-review.md").read_text(
        encoding="utf-8"
    )
    allow = json.loads(
        (_root / "config" / "obs" / "allowed_pr_authors.json").read_text(
            encoding="utf-8"
        )
    )
    assert isinstance(allow, list) and allow

    bots_match = re.search(
        r"(?ms)^  bots:\n((?:    - \"[^\"]+\"\n)+)",
        source,
    )
    assert bots_match is not None, "expected on.bots list in gh-aw-dependency-review.md"
    bots = re.findall(r'    - "([^"]+)"', bots_match.group(1))
    assert bots == allow, f"on.bots {bots!r} != allowed_pr_authors {allow!r}"

    trusted_match = re.search(
        r'(?m)^    trusted-users: "([^"]+)"\s*$',
        source,
    )
    assert trusted_match is not None, "expected tools.github.trusted-users override"
    trusted = [
        part.strip() for part in trusted_match.group(1).split(",") if part.strip()
    ]
    assert trusted == allow, (
        f"trusted-users {trusted!r} != allowed_pr_authors {allow!r}"
    )


def test_actions_commit_verification_contract_in_prompt() -> None:
    """Prompt must require REST facts file and the #2097 decision table."""
    source = (_root / ".github" / "workflows" / "gh-aw-dependency-review.md").read_text(
        encoding="utf-8"
    )
    assert "actions-commit-verification.json" in source
    assert "Collect Actions commit verification (REST)" in source
    assert "verified: true" in source
    assert "verified: false" in source
    assert "missing_data" in source
    assert "Do **not** call MCP `get_commit`" in source
    assert "Do **not** use MCP `get_commit`" in source
    assert "scripts/obs/collect_actions_commit_verification.py" in source
