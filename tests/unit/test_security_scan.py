"""Regression tests for scripts/obs/security-scan.sh SEC-002/SEC-022 boundaries."""

from __future__ import annotations

import os
import pathlib
import stat
import subprocess

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _write_executable(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def test_security_scan_boundaries_for_secret_classification(
    tmp_path: pathlib.Path,
) -> None:
    repo = tmp_path / "repo"
    workflows = repo / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "sample.yml").write_text(
        """name: sample
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - run: echo "${{ secrets.BAD }}"
      - env:
          TOKEN: ${{ secrets.OK }}
        run: echo "$TOKEN"
""",
        encoding="utf-8",
    )

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_executable(
        bin_dir / "actionlint",
        "#!/usr/bin/env bash\nprintf '[]\n'",
    )
    _write_executable(
        bin_dir / "zizmor",
        """#!/usr/bin/env bash
cat <<'JSON'
[
  {
    "ident": "secrets-outside-env",
    "desc": "secrets referenced without a dedicated environment",
    "url": "https://docs.zizmor.sh/audits/#secrets-outside-env",
    "determinations": { "severity": "Medium" },
    "locations": [
      {
        "symbolic": {
          "kind": "Primary",
          "key": { "Local": { "given_path": "./.github/workflows/sample.yml" } }
        },
        "concrete": { "location": { "start_point": { "row": 8 } } }
      }
    ]
  }
]
JSON
""",
    )

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:/usr/bin:/bin"
    result = subprocess.run(
        ["bash", str(SCRIPT), str(repo), "secrets"],
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    findings = [line for line in result.stdout.splitlines() if line.strip()]

    sec_002 = [line for line in findings if "|SEC-002|high|" in line]
    sec_022 = [line for line in findings if "|SEC-022|medium|" in line]

    assert sec_002, findings
    assert len(sec_002) == 1, sec_002
    assert sec_002[0].startswith(".github/workflows/sample.yml|7|SEC-002|high|"), (
        sec_002
    )
    assert any("run command text interpolates" in line for line in sec_002), sec_002
    assert sec_022, findings
    assert any("zizmor [secrets-outside-env]" in line for line in sec_022), sec_022
