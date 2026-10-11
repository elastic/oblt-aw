"""Regression tests for scripts/obs/security-scan.sh rule boundaries."""

from __future__ import annotations

import os
import pathlib
import stat
import subprocess
from textwrap import dedent

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _write_executable(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_scan(
    repo_root: pathlib.Path, fake_bin: pathlib.Path, category: str | None = None
) -> list[str]:
    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    args = ["bash", str(SCRIPT), str(repo_root)]
    if category:
        args.append(category)
    result = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def test_actionlint_secret_message_is_classified_as_sec_010(
    tmp_path: pathlib.Path,
) -> None:
    repo_root = tmp_path / "repo"
    workflow_dir = repo_root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yml").write_text(
        "name: test\non: workflow_dispatch\n", "utf-8"
    )

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "actionlint",
        dedent(
            """\
            #!/usr/bin/env bash
            cat <<'JSON'
            [{"kind":"expression","filepath":".github/workflows/test.yml","line":7,"message":"secret from untrusted context"}]
            JSON
            """
        ),
    )

    lines = _run_scan(repo_root, fake_bin)
    assert any(
        "|SEC-010|" in line and "actionlint [expression]" in line for line in lines
    )
    assert not any("|SEC-002|" in line for line in lines)


def test_zizmor_secrets_outside_env_is_classified_as_sec_022(
    tmp_path: pathlib.Path,
) -> None:
    repo_root = tmp_path / "repo"
    workflow_dir = repo_root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yml").write_text(
        "name: test\non: workflow_dispatch\n", "utf-8"
    )

    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    _write_executable(
        fake_bin / "zizmor",
        dedent(
            """\
            #!/usr/bin/env bash
            cat <<'JSON'
            [{
              "ident":"secrets-outside-env",
              "desc":"secrets referenced without a dedicated environment",
              "url":"https://docs.zizmor.sh/audits/#secrets-outside-env",
              "determinations":{"severity":"medium"},
              "locations":[
                {
                  "symbolic":{"kind":"Primary","key":{"Local":{"given_path":".github/workflows/test.yml"}}},
                  "concrete":{"location":{"start_point":{"row":49}}}
                }
              ]
            }]
            JSON
            """
        ),
    )

    lines = _run_scan(repo_root, fake_bin, "secrets")
    assert any(
        "|SEC-022|" in line and "zizmor [secrets-outside-env]" in line for line in lines
    )
    assert not any("|SEC-002|" in line for line in lines)
