from __future__ import annotations

import json
import os
import pathlib
import stat
import subprocess

import pytest

ROOT = pathlib.Path(__file__).parent.parent
SECURITY_SCAN = ROOT / "scripts" / "obs" / "security-scan.sh"


def _write_fake_semgrep(bin_dir: pathlib.Path, result: dict[str, object]) -> None:
    semgrep = bin_dir / "semgrep"
    payload = json.dumps({"results": [result]})
    semgrep.write_text(
        "#!/usr/bin/env sh\n"
        f"printf '%s\\n' '{payload}'\n",
        encoding="utf-8",
    )
    semgrep.chmod(semgrep.stat().st_mode | stat.S_IEXEC)


def _run_scan(tmp_path: pathlib.Path, check_id: str) -> str:
    repo = tmp_path / "repo"
    workflow_dir = repo / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "test.yml").write_text(
        "name: test\non: workflow_dispatch\njobs: {}\n", encoding="utf-8"
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_semgrep(
        fake_bin,
        {
            "path": ".github/workflows/test.yml",
            "start": {"line": 3},
            "check_id": check_id,
            "extra": {"message": "synthetic semgrep finding", "severity": "ERROR"},
        },
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:/usr/bin:/bin"
    completed = subprocess.run(
        ["bash", str(SECURITY_SCAN), str(repo)],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return completed.stdout


@pytest.mark.parametrize(
    ("check_id", "expected_rule"),
    [
        ("github-actions.hardcoded-secret", "SEC-020"),
        ("github-actions.secret-in-command", "SEC-002"),
        ("github-actions.template-injection", "SEC-010"),
        ("github-actions.workflow-oddity", "SEC-012"),
    ],
)
def test_semgrep_check_id_maps_to_expected_sec_rule(
    tmp_path: pathlib.Path, check_id: str, expected_rule: str
) -> None:
    output = _run_scan(tmp_path, check_id)
    line = next(
        row
        for row in output.splitlines()
        if row and "|3|" in row and "semgrep [" in row
    )
    assert f"|{expected_rule}|" in line
