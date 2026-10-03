"""Regression tests for scripts/obs/security-scan.sh security rule boundaries."""

from __future__ import annotations

import os
import pathlib
import stat
import subprocess

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _write_tool(path: pathlib.Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _run_scan(
    repo_root: pathlib.Path, *, actionlint_json: str, zizmor_json: str
) -> str:
    fake_bin = repo_root / "fake-bin"
    fake_bin.mkdir()

    _write_tool(
        fake_bin / "actionlint",
        "#!/usr/bin/env bash\nprintf '%s\\n' \"${ACTIONLINT_JSON:-[]}\"\n",
    )
    _write_tool(
        fake_bin / "zizmor",
        "#!/usr/bin/env bash\nprintf '%s\\n' \"${ZIZMOR_JSON:-[]}\"\n",
    )
    _write_tool(
        fake_bin / "semgrep",
        "#!/usr/bin/env bash\nprintf '%s\\n' '{\"results\":[]}'\n",
    )

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["TMPDIR"] = "/tmp/gh-aw/agent"
    env["ACTIONLINT_JSON"] = actionlint_json
    env["ZIZMOR_JSON"] = zizmor_json

    result = subprocess.run(
        [str(SCRIPT), str(repo_root)],
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_security_scan_maps_secrets_outside_env_to_sec_022(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    workflow = workflows / "demo.yml"
    workflow.write_text(
        "name: demo\non: workflow_dispatch\njobs: {}\n", encoding="utf-8"
    )

    zizmor_json = (
        "[{"
        '"ident":"secrets-outside-env",'
        '"desc":"secrets referenced without a dedicated environment",'
        '"url":"https://docs.zizmor.sh/audits/#secrets-outside-env",'
        '"determinations":{"severity":"Medium"},'
        '"locations":[{'
        '"symbolic":{"kind":"Primary","key":{"Local":{"given_path":"'
        + str(workflow)
        + '"}}},'
        '"concrete":{"location":{"start_point":{"row":9}}}'
        "}]"
        "}]"
    )

    output = _run_scan(tmp_path, actionlint_json="[]", zizmor_json=zizmor_json)
    assert "SEC-022" in output
    assert "SEC-002" not in output


def test_security_scan_keeps_actionlint_secret_expressions_in_sec_010(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "demo.yml").write_text(
        "name: demo\non: workflow_dispatch\njobs: {}\n", encoding="utf-8"
    )

    actionlint_json = (
        "[{"
        '"kind":"expression",'
        '"filepath":".github/workflows/demo.yml",'
        '"line":7,'
        '"message":"secret value from untrusted context may be injected"'
        "}]"
    )

    output = _run_scan(tmp_path, actionlint_json=actionlint_json, zizmor_json="[]")
    assert "SEC-010" in output
    assert "SEC-002" not in output
