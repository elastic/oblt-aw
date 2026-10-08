"""Regression tests for SEC-002 filtering in scripts/obs/security-scan.sh."""

from __future__ import annotations

import json
import os
import pathlib
import stat
import subprocess

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _write_workflow(path: pathlib.Path, content: str) -> int:
    path.write_text(content.strip() + "\n", encoding="utf-8")
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if "${{ secrets." in line:
            return idx
    raise AssertionError(f"secret reference line not found in {path}")


def _make_zizmor_stub(bin_dir: pathlib.Path, findings: list[dict]) -> None:
    stub = bin_dir / "zizmor"
    payload = json.dumps(findings)
    stub.write_text(
        f"#!/usr/bin/env bash\ncat <<'JSON'\n{payload}\nJSON\n",
        encoding="utf-8",
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)


def _finding(
    path: pathlib.Path, row: int, ident: str, severity: str = "Medium"
) -> dict:
    return {
        "ident": ident,
        "desc": f"{ident} test finding",
        "url": "https://docs.zizmor.sh/audits/",
        "determinations": {"severity": severity},
        "locations": [
            {
                "symbolic": {
                    "kind": "Primary",
                    "key": {"Local": {"given_path": str(path)}},
                },
                "concrete": {"location": {"start_point": {"row": row}}},
            }
        ],
    }


def test_sec002_keeps_run_interpolation_only_and_drops_lock_workflows(
    tmp_path: pathlib.Path,
) -> None:
    repo = tmp_path / "repo"
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    run_path = workflows / "run-secret.yml"
    run_line = _write_workflow(
        run_path,
        """
        jobs:
          demo:
            runs-on: ubuntu-latest
            steps:
              - run: echo "${{ secrets.GITHUB_TOKEN }}"
        """,
    )

    env_only_path = workflows / "env-only.yml"
    env_only_line = _write_workflow(
        env_only_path,
        """
        jobs:
          demo:
            runs-on: ubuntu-latest
            steps:
              - env:
                  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
                run: echo ok
        """,
    )

    lock_path = workflows / "generated.lock.yml"
    lock_line = _write_workflow(
        lock_path,
        """
        jobs:
          demo:
            runs-on: ubuntu-latest
            steps:
              - run: echo "${{ secrets.GITHUB_TOKEN }}"
        """,
    )

    findings = [
        _finding(run_path, run_line - 1, "secrets-outside-env"),
        _finding(env_only_path, env_only_line - 1, "secrets-outside-env"),
        _finding(lock_path, lock_line - 1, "secrets-outside-env"),
        _finding(lock_path, lock_line - 1, "unredacted-secrets"),
    ]
    _make_zizmor_stub(bin_dir, findings)

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    result = subprocess.run(
        ["bash", str(SCRIPT), str(repo), "secrets"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr

    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert any("|SEC-002|" in line and "run-secret.yml" in line for line in lines)
    assert not any("|SEC-002|" in line and "env-only.yml" in line for line in lines)
    assert not any(
        "|SEC-002|" in line and "generated.lock.yml" in line for line in lines
    )
    assert any("|SEC-021|" in line and "generated.lock.yml" in line for line in lines)
