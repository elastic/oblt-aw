"""Contract: APM model overrides reach the compiled agent step.

Each in-repo agent that accepts ``inputs.model`` must keep:
- ``engine.model: ${{ inputs.model }}`` in the source markdown
- a non-empty ``workflow_call`` input default of ``gpt-5.3-codex``
- activation feeding ``GH_AW_MODEL_SELECTOR`` from ``${{ inputs.model }}``
- metadata ``agent_model`` and every ``COPILOT_MODEL`` bound through
  ``needs.activation.outputs.model-selector`` (gh-aw >= v1.3.x routing)

A recompile that bakes a literal model would break APM overrides while still
passing wrapper forwarding checks that only assert the wrapper ``with:`` map.
"""

from __future__ import annotations

import json
import pathlib
import re
from typing import Any

import pytest
import yaml

_ROOT = pathlib.Path(__file__).resolve().parents[2]
_WORKFLOWS = _ROOT / ".github" / "workflows"

# In-repo agents that expose APM-overridable model selection (#2415).
_AGENT_BASENAMES = (
    "gh-aw-autoapprove",
    "gh-aw-create-pr-from-issue",
    "gh-aw-dependency-review",
    "gh-aw-docs-patrol",
    "gh-aw-estc-pr-buildkite-detective",
    "gh-aw-pr-actions-detective",
    "gh-aw-repo-scheduled",
)

_DEFAULT_MODEL = "gpt-5.3-codex"
_MODEL_INPUT_EXPR = "${{ inputs.model }}"
_MODEL_SELECTOR_EXPR = "${{ needs.activation.outputs.model-selector }}"
_MODEL_SELECTOR_ENV = 'GH_AW_MODEL_SELECTOR: "${{ inputs.model }}"'
_METADATA_RE = re.compile(
    r"^# gh-aw-metadata:\s*(\{.*\})\s*$",
    re.MULTILINE,
)


def _load_yaml(path: pathlib.Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{path}: expected mapping root"
    return data


def _workflow_on_block(workflow: dict[str, Any]) -> dict[str, Any]:
    """Return the ``on`` mapping; PyYAML 1.1 may parse the key ``on`` as ``True``."""
    on_block = workflow.get("on")
    if on_block is None:
        on_block = workflow.get(True)
    assert isinstance(on_block, dict), "workflow missing on: mapping"
    return on_block


def _frontmatter(md_text: str) -> dict[str, Any]:
    parts = md_text.split("---", 2)
    assert len(parts) >= 3, "workflow markdown missing YAML frontmatter"
    data = yaml.safe_load(parts[1])
    assert isinstance(data, dict), "frontmatter must be a mapping"
    return data


def _agent_model_from_lock(lock_text: str) -> str:
    match = _METADATA_RE.search(lock_text)
    assert match is not None, "lock missing gh-aw-metadata header"
    meta = json.loads(match.group(1))
    agent_model = meta.get("agent_model")
    assert isinstance(agent_model, str) and agent_model, "agent_model missing"
    return agent_model


def _collect_copilot_models(node: Any, found: list[str]) -> None:
    if isinstance(node, dict):
        if "COPILOT_MODEL" in node:
            value = node["COPILOT_MODEL"]
            assert isinstance(value, str), (
                f"COPILOT_MODEL must be a string, got {value!r}"
            )
            found.append(value)
        for child in node.values():
            _collect_copilot_models(child, found)
    elif isinstance(node, list):
        for child in node:
            _collect_copilot_models(child, found)


@pytest.mark.parametrize("basename", _AGENT_BASENAMES)
def test_agent_model_override_contract(basename: str) -> None:
    md_path = _WORKFLOWS / f"{basename}.md"
    lock_path = _WORKFLOWS / f"{basename}.lock.yml"
    assert md_path.is_file(), f"missing source {md_path.name}"
    assert lock_path.is_file(), f"missing lock {lock_path.name}"

    frontmatter = _frontmatter(md_path.read_text(encoding="utf-8"))
    engine = frontmatter.get("engine")
    assert isinstance(engine, dict), f"{md_path.name}: missing engine mapping"
    assert engine.get("model") == _MODEL_INPUT_EXPR, (
        f"{md_path.name}: engine.model must be {_MODEL_INPUT_EXPR!r} "
        f"(got {engine.get('model')!r})"
    )

    lock_text = lock_path.read_text(encoding="utf-8")
    assert _agent_model_from_lock(lock_text) == _MODEL_SELECTOR_EXPR, (
        f"{lock_path.name}: metadata agent_model must stay {_MODEL_SELECTOR_EXPR!r}"
    )
    assert _MODEL_SELECTOR_ENV in lock_text, (
        f"{lock_path.name}: activation must feed GH_AW_MODEL_SELECTOR "
        f"from {_MODEL_INPUT_EXPR!r}"
    )

    lock = _load_yaml(lock_path)
    workflow_call = _workflow_on_block(lock).get("workflow_call") or {}
    inputs = workflow_call.get("inputs") or {}
    assert isinstance(inputs, dict), f"{lock_path.name}: missing workflow_call.inputs"
    model_input = inputs.get("model")
    assert isinstance(model_input, dict), f"{lock_path.name}: missing model input"
    assert model_input.get("default") == _DEFAULT_MODEL, (
        f"{lock_path.name}: model default must be {_DEFAULT_MODEL!r} "
        f"(got {model_input.get('default')!r})"
    )

    copilot_models: list[str] = []
    _collect_copilot_models(lock, copilot_models)
    assert copilot_models, f"{lock_path.name}: expected at least one COPILOT_MODEL"
    for value in copilot_models:
        assert "needs.activation.outputs.model-selector" in value, (
            f"{lock_path.name}: COPILOT_MODEL must reference "
            f"needs.activation.outputs.model-selector (got {value!r})"
        )
        assert _DEFAULT_MODEL not in value, (
            f"{lock_path.name}: COPILOT_MODEL must not bake "
            f"{_DEFAULT_MODEL!r} (got {value!r})"
        )
