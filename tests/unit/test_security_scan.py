"""Tests for scripts/obs/security-scan.sh secret rule mapping."""

from __future__ import annotations

import json
import os
import pathlib
import shutil
import stat
import subprocess

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def test_secrets_outside_env_maps_to_sec003_except_run_interpolation(
    tmp_path: pathlib.Path,
) -> None:
    repo = tmp_path / "repo"
    workflow_dir = repo / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow = workflow_dir / "sample.yml"
    workflow.write_text(
        """name: sample
on: workflow_dispatch
jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ secrets.RUN_TOKEN }}"
      - uses: actions/github-script@v7
        with:
          github-token: ${{ secrets.WITH_TOKEN }}
""",
        encoding="utf-8",
    )

    findings = [
        {
            "ident": "secrets-outside-env",
            "desc": "secrets referenced in run command text",
            "url": "https://docs.zizmor.sh/audits/#secrets-outside-env",
            "determinations": {"severity": "medium"},
            "locations": [
                {
                    "symbolic": {
                        "kind": "Primary",
                        "key": {"Local": {"given_path": str(workflow)}},
                    },
                    "concrete": {"location": {"start_point": {"row": 6}}},
                }
            ],
        },
        {
            "ident": "secrets-outside-env",
            "desc": "secrets referenced outside dedicated env",
            "url": "https://docs.zizmor.sh/audits/#secrets-outside-env",
            "determinations": {"severity": "medium"},
            "locations": [
                {
                    "symbolic": {
                        "kind": "Primary",
                        "key": {"Local": {"given_path": str(workflow)}},
                    },
                    "concrete": {"location": {"start_point": {"row": 9}}},
                }
            ],
        },
    ]

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    jq_path = shutil.which("jq")
    assert jq_path is not None
    os.symlink(jq_path, bin_dir / "jq")

    zizmor = bin_dir / "zizmor"
    zizmor.write_text(
        f"#!/usr/bin/env bash\ncat <<'JSON'\n{json.dumps(findings)}\nJSON\n",
        encoding="utf-8",
    )
    zizmor.chmod(zizmor.stat().st_mode | stat.S_IEXEC)

    result = subprocess.run(
        ["bash", str(SCRIPT), str(repo), "secrets"],
        env={"PATH": f"{bin_dir}:/usr/bin:/bin", "TMPDIR": "/tmp/gh-aw/agent"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    rows = [line.split("|", 4) for line in result.stdout.strip().splitlines() if line]
    findings_by_line = {(file, line): (rule, sev) for file, line, rule, sev, _ in rows}

    assert findings_by_line[(".github/workflows/sample.yml", "7")] == (
        "SEC-002",
        "high",
    )
    assert findings_by_line[(".github/workflows/sample.yml", "10")] == (
        "SEC-003",
        "medium",
    )
