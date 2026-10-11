"""Regression tests for scripts/obs/security-scan.sh."""

from __future__ import annotations

import os
import pathlib
import stat
import subprocess

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _write_workflow(repo_root: pathlib.Path, content: str) -> pathlib.Path:
    workflows = repo_root / ".github" / "workflows"
    workflows.mkdir(parents=True, exist_ok=True)
    workflow = workflows / "sample.yml"
    workflow.write_text(content, encoding="utf-8")
    return workflow


def _run_security_scan(
    repo_root: pathlib.Path,
    *,
    env_overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["bash", str(SCRIPT), str(repo_root), "secrets"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_sec_002_detects_secret_interpolation_in_run_block(
    tmp_path: pathlib.Path,
) -> None:
    github_token_expr = "${{ " + "secrets.GITHUB_TOKEN }}"
    buildkite_token_expr = "${{ " + "secrets.BUILDKITE_TOKEN }}"
    _write_workflow(
        tmp_path,
        f"""
name: sec-002-positive
on: workflow_dispatch
jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - run: echo "bad {github_token_expr}"
      - run: |
          echo "also bad"
          curl -H "Authorization: Bearer {buildkite_token_expr}" https://example.invalid
""".strip()
        + "\n",
    )

    result = _run_security_scan(tmp_path)
    assert result.returncode == 0, result.stderr
    findings = [line for line in result.stdout.splitlines() if "|SEC-002|" in line]
    assert findings, result.stdout
    assert any("command string" in line for line in findings)
    assert any("command block" in line for line in findings)


def test_sec_002_ignores_env_indirection_only(tmp_path: pathlib.Path) -> None:
    github_token_expr = "${{ " + "secrets.GITHUB_TOKEN }}"
    _write_workflow(
        tmp_path,
        f"""
name: sec-002-negative
on: workflow_dispatch
jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - env:
          GH_TOKEN: {github_token_expr}
        run: gh api /repos/${{ github.repository }}
""".strip()
        + "\n",
    )

    result = _run_security_scan(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "|SEC-002|" not in result.stdout, result.stdout


def test_secrets_outside_env_is_mapped_to_sec_022(tmp_path: pathlib.Path) -> None:
    workflow = _write_workflow(
        tmp_path,
        """
name: zizmor-remap
on: workflow_dispatch
jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - run: echo ok
""".strip()
        + "\n",
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(parents=True)
    fake_zizmor = bin_dir / "zizmor"
    fake_zizmor.write_text(
        f"""#!/usr/bin/env bash
cat <<'JSON'
[
  {{
    "ident": "secrets-outside-env",
    "desc": "secrets referenced without a dedicated environment",
    "url": "https://docs.zizmor.sh/audits/#secrets-outside-env",
    "determinations": {{"severity": "Medium"}},
    "locations": [
      {{
        "symbolic": {{"kind": "Primary", "key": {{"Local": {{"given_path": "{workflow}"}}}}}},
        "concrete": {{"location": {{"start_point": {{"row": 7}}}}}}
      }}
    ]
  }}
]
JSON
""",
        encoding="utf-8",
    )
    fake_zizmor.chmod(fake_zizmor.stat().st_mode | stat.S_IEXEC)

    result = _run_security_scan(
        tmp_path,
        env_overrides={"PATH": f"{bin_dir}:{os.environ.get('PATH', '')}"},
    )
    assert result.returncode == 0, result.stderr
    assert "|SEC-022|" in result.stdout, result.stdout
    assert "|SEC-002|" not in result.stdout, result.stdout
