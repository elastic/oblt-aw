from __future__ import annotations

import json
import os
import pathlib
import stat
import subprocess
import tempfile


def _write_mock_semgrep(bin_dir: pathlib.Path, payload: dict[str, object]) -> None:
    semgrep = bin_dir / "semgrep"
    semgrep.write_text(
        "#!/usr/bin/env bash\n"
        "cat <<'JSON'\n"
        f"{json.dumps(payload)}\n"
        "JSON\n"
    )
    semgrep.chmod(semgrep.stat().st_mode | stat.S_IXUSR)


def test_semgrep_check_id_mapping() -> None:
    root = pathlib.Path(__file__).parent.parent
    scan_script = root / "scripts" / "obs" / "security-scan.sh"

    with tempfile.TemporaryDirectory() as td:
        tmpdir = pathlib.Path(td)
        repo = tmpdir / "repo"
        (repo / ".github" / "workflows").mkdir(parents=True)
        (repo / ".github" / "workflows" / "ci.yml").write_text("name: ci\n")
        bin_dir = tmpdir / "bin"
        bin_dir.mkdir()

        payload = {
            "results": [
                {
                    "path": str(repo / ".github" / "workflows" / "ci.yml"),
                    "start": {"line": 11},
                    "check_id": "github-actions.hardcoded-secret",
                    "extra": {"message": "hardcoded secret", "severity": "ERROR"},
                },
                {
                    "path": str(repo / ".github" / "workflows" / "ci.yml"),
                    "start": {"line": 12},
                    "check_id": "github-actions.secret-env",
                    "extra": {"message": "secret in workflow", "severity": "WARNING"},
                },
                {
                    "path": str(repo / ".github" / "workflows" / "ci.yml"),
                    "start": {"line": 13},
                    "check_id": "github-actions.template-injection",
                    "extra": {"message": "template injection", "severity": "ERROR"},
                },
                {
                    "path": str(repo / ".github" / "workflows" / "ci.yml"),
                    "start": {"line": 14},
                    "check_id": "github-actions.misc-rule",
                    "extra": {"message": "misc finding", "severity": "INFO"},
                },
            ]
        }
        _write_mock_semgrep(bin_dir, payload)

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        out = subprocess.run(
            [str(scan_script), str(repo)],
            env=env,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.splitlines()

    semgrep_rules = {}
    for line in out:
        _file_path, _line, rule, _sev, message = line.split("|", 4)
        if message.startswith("semgrep ["):
            check_id = message.split("semgrep [", 1)[1].split("]:", 1)[0]
            semgrep_rules[check_id] = rule

    assert semgrep_rules["github-actions.hardcoded-secret"] == "SEC-020"
    assert semgrep_rules["github-actions.secret-env"] == "SEC-002"
    assert semgrep_rules["github-actions.template-injection"] == "SEC-010"
    assert semgrep_rules["github-actions.misc-rule"] == "SEC-012"
