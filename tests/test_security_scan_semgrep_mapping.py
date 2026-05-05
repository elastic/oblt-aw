import json
import os
import stat
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SECURITY_SCAN_SCRIPT = REPO_ROOT / "scripts/security-scan.sh"


def test_semgrep_findings_map_to_correct_sec_rules(tmp_path: Path) -> None:
    repo_dir = tmp_path / "repo"
    workflow_dir = repo_dir / ".github/workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "sample.yml").write_text("name: sample\non: push\njobs: {}\n", encoding="utf-8")

    semgrep_results = {
        "results": [
            {
                "path": str(workflow_dir / "sample.yml"),
                "start": {"line": 3},
                "check_id": "p/github-actions/security/secrets-in-workflow",
                "extra": {"message": "secret interpolation in run command", "severity": "ERROR"},
            },
            {
                "path": str(workflow_dir / "sample.yml"),
                "start": {"line": 4},
                "check_id": "p/github-actions/security/hardcoded-credential",
                "extra": {"message": "hardcoded credential value found", "severity": "ERROR"},
            },
            {
                "path": str(workflow_dir / "sample.yml"),
                "start": {"line": 5},
                "check_id": "p/github-actions/security/expression-injection",
                "extra": {"message": "expression injection risk", "severity": "ERROR"},
            },
            {
                "path": str(workflow_dir / "sample.yml"),
                "start": {"line": 6},
                "check_id": "p/github-actions/security/matrix-user-input",
                "extra": {"message": "user-controlled matrix value", "severity": "WARNING"},
            },
        ]
    }

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    fake_semgrep = fake_bin / "semgrep"
    fake_semgrep.write_text(
        "#!/usr/bin/env bash\n"
        "cat <<'JSON'\n"
        f"{json.dumps(semgrep_results)}\n"
        "JSON\n",
        encoding="utf-8",
    )
    fake_semgrep.chmod(fake_semgrep.stat().st_mode | stat.S_IEXEC)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"

    result = subprocess.run(
        ["bash", str(SECURITY_SCAN_SCRIPT), str(repo_dir)],
        capture_output=True,
        text=True,
        check=True,
        env=env,
    )

    findings_by_line = {}
    for line in result.stdout.splitlines():
        _file_path, line_no, sec_rule, _severity, _message = line.split("|", 4)
        findings_by_line[line_no] = sec_rule

    assert findings_by_line["3"] == "SEC-002"
    assert findings_by_line["4"] == "SEC-020"
    assert findings_by_line["5"] == "SEC-010"
    assert findings_by_line["6"] == "SEC-012"
