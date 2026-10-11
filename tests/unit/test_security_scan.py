"""Regression tests for scripts/obs/security-scan.sh SEC-002 boundaries."""

from __future__ import annotations

import os
import pathlib
import subprocess
import textwrap

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _write_executable(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)


def _run_scan(
    repo_root: pathlib.Path, mock_bin: pathlib.Path | None = None
) -> list[str]:
    env = os.environ.copy()
    if mock_bin is not None:
        env["PATH"] = f"{mock_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(SCRIPT), str(repo_root), "secrets"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_sec002_detects_secret_interpolation_in_run_block(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    workflow = workflows / "example.yml"
    workflow.write_text(
        textwrap.dedent(
            """\
            name: test
            on:
              workflow_dispatch:
            jobs:
              check:
                runs-on: ubuntu-latest
                steps:
                  - name: bad
                    run: |
                      echo "${{ secrets.GITHUB_TOKEN }}"
            """
        ),
        encoding="utf-8",
    )

    findings = _run_scan(tmp_path)
    assert any(
        line.startswith(".github/workflows/example.yml|10|SEC-002|high|")
        for line in findings
    )


def test_secret_boundary_reclassifies_non_run_secret_contexts(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "test.yml").write_text(
        textwrap.dedent(
            """\
            name: test
            on:
              workflow_dispatch:
            jobs:
              check:
                runs-on: ubuntu-latest
                steps:
                  - uses: actions/github-script@v7
                    with:
                      github-token: ${{ secrets.GITHUB_TOKEN }}
            """
        ),
        encoding="utf-8",
    )
    (workflows / "test.lock.yml").write_text("name: generated\n", encoding="utf-8")

    mock_bin = tmp_path / "bin"
    mock_bin.mkdir()
    _write_executable(
        mock_bin / "actionlint",
        "#!/usr/bin/env bash\n"
        'echo \'[{"kind":"expression","filepath":".github/workflows/test.yml",'
        '"line":10,"message":"secret referenced in expression"}]\'\n',
    )
    _write_executable(
        mock_bin / "zizmor",
        "#!/usr/bin/env bash\n"
        'echo \'[{"ident":"secrets-outside-env","determinations":{"severity":"medium"},'
        '"desc":"secrets referenced without env","url":"https://docs.zizmor.sh/audits/#secrets-outside-env",'
        '"locations":[{"symbolic":{"kind":"Primary","key":{"Local":{"given_path":".github/workflows/test.lock.yml"}}},'
        '"concrete":{"location":{"start_point":{"row":4}}}}]}]\'\n',
    )

    findings = _run_scan(tmp_path, mock_bin)
    assert not any("|SEC-002|" in line for line in findings)
    assert any(
        line.startswith(".github/workflows/test.lock.yml|5|SEC-022|medium|")
        for line in findings
    )
