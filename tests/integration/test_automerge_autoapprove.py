"""
Integration checks for obs:automerge approve → gh-aw-autoapprove.

Proves wrapper ↔ aw-resolve-agentic-assets ↔ lock input wiring. Does not
invoke a live model or mint tokens.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

import yaml

_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "scripts"))

WRAPPER_BASENAME = "obs-aw-automerge.yml"
LOCK_BASENAME = "gh-aw-autoapprove.lock.yml"
SOURCE_BASENAME = "gh-aw-autoapprove.md"
RESOLVE_JOB = "resolve-apm-assets"
AGENT_JOB = "approve"

WRAPPER_PATH = _root / ".github" / "workflows" / WRAPPER_BASENAME
LOCK_PATH = _root / ".github" / "workflows" / LOCK_BASENAME
SOURCE_PATH = _root / ".github" / "workflows" / SOURCE_BASENAME
ALLOWED_PR_AUTHORS = _root / "config" / "obs" / "allowed_pr_authors.json"


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


class TestAutomergeAutoapproveWrapperLockWiring:
    """Static contract: wrapper maps resolve outputs onto the autoapprove lock."""

    def test_resolve_job_targets_wrapper_basename(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        resolve_job = wrapper["jobs"][RESOLVE_JOB]
        assert resolve_job["uses"].endswith("aw-resolve-agentic-assets.yml"), (
            f"unexpected resolve uses: {resolve_job['uses']!r}"
        )
        assert resolve_job["with"]["workflow-basename"] == WRAPPER_BASENAME
        assert "platform-additional-instructions" not in (resolve_job.get("with") or {})

    def test_approve_job_passes_resolve_outputs_to_lock_inputs(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        lock = _load_yaml(LOCK_PATH)
        agent = wrapper["jobs"][AGENT_JOB]
        with_block = agent.get("with") or {}

        uses = agent["uses"]
        assert isinstance(uses, str)
        assert uses.startswith(
            ("elastic/oblt-aw/.github/workflows/", "./.github/workflows/")
        ), (
            f"{AGENT_JOB} must call in-repo lock via absolute elastic/oblt-aw or "
            f"relative ./ path (got {uses!r}; rollback to elastic/ai-github-actions "
            "must fail)"
        )
        assert LOCK_BASENAME in uses, f"{AGENT_JOB} must call in-repo {LOCK_BASENAME}"
        assert "gh-aw-mention-in-pr" not in uses

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
        assert with_block.get("github-token-policy") == (
            "${{ github.event.pull_request.user.login == 'github-actions[bot]' "
            "&& inputs.shared-token-policy || '' }}"
        )
        for dropped in (
            "allowed-bot-users",
            "prompt",
            "report-failure-as-issue",
        ):
            assert dropped not in with_block, (
                f"{AGENT_JOB} must not pass simplified-away input {dropped!r}"
            )

        lock_inputs = _lock_workflow_call_inputs(lock)
        for key in (
            "additional-instructions",
            "setup-commands",
            "github-token-policy",
        ):
            assert key in lock_inputs, (
                f"{LOCK_BASENAME} must declare workflow_call input {key!r}"
            )
        for dropped in (
            "allowed-bot-users",
            "messages-footer",
            "model",
            "prompt",
            "report-failure-as-issue",
        ):
            assert dropped not in lock_inputs, (
                f"{LOCK_BASENAME} must not expose simplified-away input {dropped!r}"
            )

    def test_approve_job_does_not_invoke_agent_engine_inline(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        agent = wrapper["jobs"][AGENT_JOB]
        assert "uses" in agent
        assert "steps" not in agent


def test_hardcoded_bots_match_allowed_pr_authors() -> None:
    """Source on.bots / trusted-users must stay aligned with allowed_pr_authors.json."""
    source = SOURCE_PATH.read_text(encoding="utf-8")
    allow = json.loads(ALLOWED_PR_AUTHORS.read_text(encoding="utf-8"))
    assert isinstance(allow, list) and allow

    bots_match = re.search(
        r"(?ms)^  bots:\n((?:    - \"[^\"]+\"\n)+)",
        source,
    )
    assert bots_match is not None, f"expected on.bots list in {SOURCE_BASENAME}"
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


def test_autoapprove_prompt_requires_approve_not_comment() -> None:
    """Prompt must require APPROVE and forbid COMMENT eligibility / request-changes."""
    source = SOURCE_PATH.read_text(encoding="utf-8")
    assert "submit_pull_request_review" in source
    assert "event=APPROVE" in source
    assert (
        "Do not use `event=COMMENT`" in source or "Do not use event=COMMENT" in source
    )
    assert "do not request changes" in source.lower()
    assert "oblt-aw/ai/merge-ready" in source
    assert "check-run" in source.lower() or "commit status" in source.lower()
    assert "autoapprove only" in source.lower() or "autoapprove" in source.lower()


def test_lock_and_source_exist() -> None:
    assert SOURCE_PATH.is_file()
    assert LOCK_PATH.is_file()
