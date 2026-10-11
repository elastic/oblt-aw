"""Tests for scripts/obs/security-scan.sh."""

from __future__ import annotations

import pathlib
import subprocess
import textwrap

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _run_security_scan(repo_root: pathlib.Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), str(repo_root), "secrets"],
        capture_output=True,
        text=True,
        check=False,
    )


def _sec002_lines(scan_output: str) -> list[str]:
    return [line for line in scan_output.splitlines() if "|SEC-002|" in line]


def test_sec002_detects_inline_run_secret_interpolation(tmp_path: pathlib.Path) -> None:
    workflow = tmp_path / ".github" / "workflows" / "inline.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        textwrap.dedent(
            """\
            name: Inline
            on: workflow_dispatch
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - run: echo "token=${{ secrets.GITHUB_TOKEN }}"
            """
        ),
        encoding="utf-8",
    )

    result = _run_security_scan(tmp_path)

    assert result.returncode == 0, result.stderr
    sec002 = _sec002_lines(result.stdout)
    assert any(
        line.startswith(".github/workflows/inline.yml|7|SEC-002|high|")
        for line in sec002
    )


def test_sec002_detects_multiline_run_secret_interpolation(
    tmp_path: pathlib.Path,
) -> None:
    workflow = tmp_path / ".github" / "workflows" / "multiline.yml"
    workflow.parent.mkdir(parents=True)
    workflow.write_text(
        textwrap.dedent(
            """\
            name: Multiline
            on: workflow_dispatch
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - run: |
                      echo start
                      curl -H "Authorization: Bearer ${{ secrets.GITHUB_TOKEN }}" https://example.test
            """
        ),
        encoding="utf-8",
    )

    result = _run_security_scan(tmp_path)

    assert result.returncode == 0, result.stderr
    sec002 = _sec002_lines(result.stdout)
    assert any(
        line.startswith(".github/workflows/multiline.yml|9|SEC-002|high|")
        for line in sec002
    )


def test_sec002_ignores_env_with_and_lock_workflows(tmp_path: pathlib.Path) -> None:
    non_run_workflow = tmp_path / ".github" / "workflows" / "env-with-only.yml"
    non_run_workflow.parent.mkdir(parents=True)
    non_run_workflow.write_text(
        textwrap.dedent(
            """\
            name: EnvOnly
            on: workflow_dispatch
            jobs:
              test:
                runs-on: ubuntu-latest
                env:
                  TOKEN: ${{ secrets.GITHUB_TOKEN }}
                steps:
                  - uses: actions/checkout@v5
                    with:
                      token: ${{ secrets.GITHUB_TOKEN }}
                  - run: echo "safe"
            """
        ),
        encoding="utf-8",
    )

    lock_workflow = tmp_path / ".github" / "workflows" / "generated.lock.yml"
    lock_workflow.write_text(
        textwrap.dedent(
            """\
            name: Generated
            on: workflow_dispatch
            jobs:
              generated:
                runs-on: ubuntu-latest
                steps:
                  - run: echo "token=${{ secrets.GITHUB_TOKEN }}"
            """
        ),
        encoding="utf-8",
    )

    result = _run_security_scan(tmp_path)

    assert result.returncode == 0, result.stderr
    assert _sec002_lines(result.stdout) == []
