"""
Integration checks for obs:estc-pr-buildkite-detective.

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

WRAPPER_BASENAME = "obs-aw-estc-pr-buildkite-detective.yml"
LOCK_BASENAME = "gh-aw-estc-pr-buildkite-detective.lock.yml"
WORKFLOW_ID = "estc-pr-buildkite-detective"
ORG_KEY = "obs"
RESOLVE_JOB = "resolve-apm-assets"
AGENT_JOB = "estc-pr-buildkite-detective"

FIXTURE_ROOT = _root / "testdata" / "agentic" / "estc-pr-buildkite-detective"
CONSUMER_ROOT = FIXTURE_ROOT / "consumer"
EXPECTED_SETUP = FIXTURE_ROOT / "expected" / "setup-commands.json"
EXPECTED_LAYERS = FIXTURE_ROOT / "expected" / "instruction-layers.json"
WRAPPER_PATH = _root / ".github" / "workflows" / WRAPPER_BASENAME
LOCK_PATH = _root / ".github" / "workflows" / LOCK_BASENAME


def _load_yaml(path: pathlib.Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path}: expected mapping root"
    return data


def _platform_additional_instructions(wrapper: dict) -> str:
    resolve_job = wrapper["jobs"][RESOLVE_JOB]
    with_block = resolve_job.get("with") or {}
    text = with_block.get("platform-additional-instructions") or ""
    assert isinstance(text, str) and text.strip(), (
        f"{WRAPPER_BASENAME}: resolve job must declare "
        "platform-additional-instructions"
    )
    return text


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


class TestEstcWrapperLockWiring:
    """Static contract: wrapper maps resolve outputs onto lock inputs."""

    def test_resolve_job_targets_wrapper_basename(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        resolve_job = wrapper["jobs"][RESOLVE_JOB]
        assert resolve_job["uses"].endswith(
            "aw-resolve-agentic-assets.yml"
        ), f"unexpected resolve uses: {resolve_job['uses']!r}"
        assert resolve_job["with"]["workflow-basename"] == WRAPPER_BASENAME

    def test_agent_job_passes_resolve_outputs_to_lock_inputs(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        lock = _load_yaml(LOCK_PATH)
        agent = wrapper["jobs"][AGENT_JOB]
        with_block = agent.get("with") or {}

        assert LOCK_BASENAME in agent["uses"], (
            f"{AGENT_JOB} must call in-repo {LOCK_BASENAME}"
        )
        needs = agent.get("needs") or []
        if isinstance(needs, str):
            needs = [needs]
        assert RESOLVE_JOB in needs, (
            f"{AGENT_JOB} must need {RESOLVE_JOB} so "
            "needs.*.outputs resolve at runtime"
        )
        assert (
            with_block.get("additional-instructions")
            == "${{ needs.resolve-apm-assets.outputs.resolved-additional-instructions }}"
        )
        assert (
            with_block.get("setup-commands")
            == "${{ join(fromJSON(needs.resolve-apm-assets.outputs."
            "resolved-setup-commands-json), '\\n') }}"
        )

        lock_inputs = _lock_workflow_call_inputs(lock)
        for key in ("additional-instructions", "setup-commands"):
            assert key in lock_inputs, (
                f"{LOCK_BASENAME} must declare workflow_call input {key!r}"
            )
            assert key in with_block, (
                f"{WRAPPER_BASENAME} agent job must pass lock input {key!r}"
            )

    def test_wrapper_does_not_invoke_agent_engine_inline(self) -> None:
        """Regression guard: wrapper must call the lock, not embed an agent job."""
        wrapper = _load_yaml(WRAPPER_PATH)
        agent = wrapper["jobs"][AGENT_JOB]
        assert "uses" in agent
        assert "steps" not in agent


class TestEstcResolveFixtures:
    """Resolve against frozen consumer fixtures (no live model / tokens)."""

    def test_resolve_maps_additional_instructions_setup_and_layers(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        platform = _platform_additional_instructions(wrapper)
        expected_setup = json.loads(EXPECTED_SETUP.read_text(encoding="utf-8"))
        expected_layers = json.loads(EXPECTED_LAYERS.read_text(encoding="utf-8"))

        resolved = resolver.resolve_agentic_assets(
            repo_root=CONSUMER_ROOT,
            workflow_id=WORKFLOW_ID,
            org_key=ORG_KEY,
            platform_additional_instructions=platform,
            config_dir=_root / "config",
            workflow_basename=WRAPPER_BASENAME,
        )

        assert resolved["asset_source"] == "workflow"
        assert resolved["setup_commands"] == expected_setup

        # Wrapper joins setup-commands JSON with newlines before the lock input.
        lock_setup_commands = "\n".join(resolved["setup_commands"])
        assert lock_setup_commands == "\n".join(expected_setup)

        text = resolved["additional_instructions"]
        assert "flaky-test" in text
        assert "ESTC_CONSUMER_FRAGMENT_MARKER" in text
        assert "ESTC_CONSUMER_INLINE_MARKER" in text
        assert "ESTC_COMMON_INLINE_SHOULD_NOT_APPLY" not in text
        assert text.index("flaky-test") < text.index("ESTC_CONSUMER_FRAGMENT_MARKER")
        assert text.index("ESTC_CONSUMER_FRAGMENT_MARKER") < text.index(
            "ESTC_CONSUMER_INLINE_MARKER"
        )

        layers = resolved["instruction_layers"]
        assert layers["org-key"] == expected_layers["org-key"]
        assert layers["workflow-id"] == expected_layers["workflow-id"]
        assert layers["workflow-basename"] == expected_layers["workflow-basename"]
        assert layers["layers"] == expected_layers["layers"]

    def test_resolve_without_apm_keeps_platform_only(
        self, tmp_path: pathlib.Path
    ) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        platform = _platform_additional_instructions(wrapper)

        resolved = resolver.resolve_agentic_assets(
            repo_root=tmp_path,
            workflow_id=WORKFLOW_ID,
            org_key=ORG_KEY,
            platform_additional_instructions=platform,
            config_dir=_root / "config",
            workflow_basename=WRAPPER_BASENAME,
        )

        assert resolved["apm_manifest_present"] is False
        assert resolved["asset_source"] == "none"
        assert resolved["setup_commands"] == []
        assert "flaky-test" in resolved["additional_instructions"]
        by_name = {
            layer["layer"]: layer for layer in resolved["instruction_layers"]["layers"]
        }
        assert by_name["platform-inline"]["present"] is True
        assert by_name["consumer-inline"]["present"] is False
        assert by_name["consumer-fragments"]["present"] is False


def test_fixture_tree_is_present() -> None:
    assert (CONSUMER_ROOT / "apm.yml").is_file()
    assert (
        CONSUMER_ROOT / ".github" / "ai" / "fragments" / "estc-fixture.md"
    ).is_file()
    assert EXPECTED_SETUP.is_file()
    assert EXPECTED_LAYERS.is_file()
