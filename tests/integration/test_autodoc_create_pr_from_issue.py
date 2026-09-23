"""
Integration checks for obs-aw-autodoc fix → gh-aw-create-pr-from-issue.

Proves wrapper ↔ aw-resolve-agentic-assets ↔ lock input wiring and that the
compiled lock excludes top-level docs from protected-files. Does not invoke a
live model.
"""

from __future__ import annotations

import json
import pathlib
import sys

import yaml

_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "scripts"))

WRAPPER_BASENAME = "obs-aw-autodoc.yml"
LOCK_BASENAME = "gh-aw-create-pr-from-issue.lock.yml"
RESOLVE_JOB = "resolve-apm-assets-fix"
FIX_JOB = "fix"

WRAPPER_PATH = _root / ".github" / "workflows" / WRAPPER_BASENAME
LOCK_PATH = _root / ".github" / "workflows" / LOCK_BASENAME
SOURCE_PATH = _root / ".github" / "workflows" / "gh-aw-create-pr-from-issue.md"

_DOCS_EXCLUDES = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "CODE_OF_CONDUCT.md",
)
_MINIMAL_LOCK_INPUTS = frozenset({"target-issue-number", "additional-instructions"})


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


def _first_safe_outputs_config(lock_text: str) -> dict:
    """Parse the first GH_AW_SAFE_OUTPUTS_CONFIG double-quoted JSON scalar.

    Avoid non-greedy ``{.*?}`` regexes: values can contain ``}`` (for example
    ``${GH_AW_INPUT_TARGET_ISSUE_NUMBER}``). Take the YAML line's quoted
    scalar and unicode-unescape it instead.
    """
    for line in lock_text.splitlines():
        if "GH_AW_SAFE_OUTPUTS_CONFIG:" not in line:
            continue
        _, _, rest = line.partition(":")
        rest = rest.strip()
        assert rest.startswith('"') and rest.endswith('"'), (
            f"{LOCK_BASENAME}: GH_AW_SAFE_OUTPUTS_CONFIG must be a double-quoted scalar"
        )
        raw = rest[1:-1].encode("utf-8").decode("unicode_escape")
        cfg = json.loads(raw)
        assert isinstance(cfg, dict)
        return cfg
    raise AssertionError(f"{LOCK_BASENAME}: missing GH_AW_SAFE_OUTPUTS_CONFIG")


class TestAutodocCreatePrWrapperLockWiring:
    """Static contract: autodoc fix maps resolve outputs onto the in-repo lock."""

    def test_resolve_job_targets_wrapper_basename(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        resolve_job = wrapper["jobs"][RESOLVE_JOB]
        assert resolve_job["uses"].endswith("aw-resolve-agentic-assets.yml"), (
            f"unexpected resolve uses: {resolve_job['uses']!r}"
        )
        assert resolve_job["with"]["workflow-basename"] == WRAPPER_BASENAME
        assert "platform-additional-instructions" not in (resolve_job.get("with") or {})

    def test_fix_job_passes_minimal_inputs_to_in_repo_lock(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        lock = _load_yaml(LOCK_PATH)
        fix = wrapper["jobs"][FIX_JOB]
        with_block = fix.get("with") or {}

        uses = fix["uses"]
        assert isinstance(uses, str)
        assert uses.startswith("elastic/oblt-aw/.github/workflows/"), (
            f"{FIX_JOB} must call in-repo lock under elastic/oblt-aw "
            f"(got {uses!r}; rollback to elastic/ai-github-actions must fail)"
        )
        assert LOCK_BASENAME in uses, f"{FIX_JOB} must call in-repo {LOCK_BASENAME}"
        needs = fix.get("needs") or []
        if isinstance(needs, str):
            needs = [needs]
        assert RESOLVE_JOB in needs, (
            f"{FIX_JOB} must need {RESOLVE_JOB} so needs.*.outputs resolve at runtime"
        )
        assert (
            with_block.get("additional-instructions")
            == "${{ needs.resolve-apm-assets-fix.outputs.resolved-additional-instructions }}"
        )
        assert (
            with_block.get("target-issue-number")
            == "${{ needs.audit.outputs.created_issue_number }}"
        )
        assert "draft-prs" not in with_block
        assert "report-failure-as-issue" not in with_block
        assert "model" not in with_block

        lock_inputs = set(_lock_workflow_call_inputs(lock))
        # Compiler may inject aw_context; require the preserved autodoc inputs and
        # reject the simplified-away surface.
        assert _MINIMAL_LOCK_INPUTS <= lock_inputs, (
            f"lock inputs missing {_MINIMAL_LOCK_INPUTS - lock_inputs}"
        )
        for dropped in (
            "draft-prs",
            "report-failure-as-issue",
            "model",
            "prompt",
            "setup-commands",
            "messages-footer",
        ):
            assert dropped not in lock_inputs, (
                f"lock must not expose simplified-away input {dropped!r}"
            )


class TestCreatePrProtectedFilesExcludes:
    def test_compiled_lock_excludes_top_level_docs(self) -> None:
        assert LOCK_PATH.is_file(), f"missing compiled lock {LOCK_PATH}"
        assert SOURCE_PATH.is_file(), f"missing source {SOURCE_PATH}"
        cfg = _first_safe_outputs_config(LOCK_PATH.read_text(encoding="utf-8"))
        create_pr = cfg.get("create_pull_request") or {}
        assert isinstance(create_pr, dict)
        assert create_pr.get("draft") is True, (
            "create_pull_request.draft must be true in compiled lock "
            f"(got {create_pr.get('draft')!r}; top-level source must not shadow "
            "safe-output-create-pr.md)"
        )
        patch_format = create_pr.get("patch_format") or create_pr.get("patch-format")
        assert patch_format == "bundle", (
            "create_pull_request.patch_format must be bundle in compiled lock "
            f"(got {patch_format!r})"
        )
        # Compiler maps github-token-for-extra-empty-commit onto the handler
        # env GH_AW_CI_TRIGGER_TOKEN (not into SAFE_OUTPUTS_CONFIG JSON).
        lock_text = LOCK_PATH.read_text(encoding="utf-8")
        assert (
            "GH_AW_CI_TRIGGER_TOKEN: ${{ secrets.EXTRA_COMMIT_GITHUB_TOKEN }}"
            in lock_text
        ), (
            "handler must map GH_AW_CI_TRIGGER_TOKEN from EXTRA_COMMIT_GITHUB_TOKEN "
            "(top-level create-pull-request shadows the fragment; field must be "
            "re-declared on the source mapping)"
        )
        policy = create_pr.get("protected_files_policy")
        assert policy in ("request_review", "request-review"), (
            f"unexpected protected_files_policy: {policy!r}"
        )
        protected = set(create_pr.get("protected_files") or [])
        for name in _DOCS_EXCLUDES:
            assert name not in protected, (
                f"{name} must be excluded from protected_files (got it listed)"
            )
        # Remaining protected paths stay gated (do not unlock everything).
        assert protected, "protected_files list must remain non-empty after excludes"


class TestAutodocNotifyNoPr:
    def test_wrapper_notifies_on_success_without_pr(self) -> None:
        wrapper = _load_yaml(WRAPPER_PATH)
        jobs = wrapper["jobs"]
        assert "notify-no-pr" in jobs, (
            "obs-aw-autodoc must notify when fix succeeds with empty created_pr_number "
            "(parity with issue/security/RNAI fixers)"
        )
        notify = jobs["notify-no-pr"]
        assert notify.get("needs") == ["audit", "fix"] or set(
            notify.get("needs") or []
        ) >= {
            "audit",
            "fix",
        }
        condition = str(notify.get("if") or "")
        assert "needs.fix.result == 'success'" in condition
        assert "created_pr_number == ''" in condition
        assert "notify-fix-failure" in jobs
        failure_if = str(jobs["notify-fix-failure"].get("if") or "")
        assert "needs.fix.result == 'failure'" in failure_if
