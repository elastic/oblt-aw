"""Regression tests for SEC-002 detector boundaries."""

from __future__ import annotations

import os
import pathlib
import subprocess
import textwrap

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def test_sec002_filters_lock_and_non_run_contexts(tmp_path: pathlib.Path) -> None:
    repo_root = tmp_path / "repo"
    workflows_dir = repo_root / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    (workflows_dir / "authored.yml").write_text(
        textwrap.dedent(
            """\
            name: SEC002
            on: workflow_dispatch
            jobs:
              test:
                runs-on: ubuntu-latest
                steps:
                  - name: Env secret
                    env:
                      API_TOKEN: ${{ secrets.API_TOKEN }}
                    run: echo "safe"
                  - name: Inline run secret
                    run: echo "${{ secrets.RUN_TOKEN }}"
            """
        ),
        encoding="utf-8",
    )
    (workflows_dir / "generated.lock.yml").write_text(
        textwrap.dedent(
            """\
            name: generated
            on: workflow_dispatch
            jobs:
              generated:
                runs-on: ubuntu-latest
                steps:
                  - run: echo "${{ secrets.LOCK_TOKEN }}"
            """
        ),
        encoding="utf-8",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "zizmor").write_text(
        textwrap.dedent(
            """\
            #!/usr/bin/env bash
            set -euo pipefail
            cat <<'JSON'
            [
              {
                "ident": "secrets-outside-env",
                "desc": "lock file secret",
                "url": "https://docs.zizmor.sh/audits/#secrets-outside-env",
                "determinations": {"severity": "Medium"},
                "locations": [
                  {
                    "symbolic": {"kind": "Primary", "key": {"Local": {"given_path": ".github/workflows/generated.lock.yml"}}},
                    "concrete": {"location": {"start_point": {"row": 7}}}
                  }
                ]
              },
              {
                "ident": "secrets-outside-env",
                "desc": "env secret",
                "url": "https://docs.zizmor.sh/audits/#secrets-outside-env",
                "determinations": {"severity": "Medium"},
                "locations": [
                  {
                    "symbolic": {"kind": "Primary", "key": {"Local": {"given_path": ".github/workflows/authored.yml"}}},
                    "concrete": {"location": {"start_point": {"row": 8}}}
                  }
                ]
              },
              {
                "ident": "secrets-outside-env",
                "desc": "run secret",
                "url": "https://docs.zizmor.sh/audits/#secrets-outside-env",
                "determinations": {"severity": "Medium"},
                "locations": [
                  {
                    "symbolic": {"kind": "Primary", "key": {"Local": {"given_path": ".github/workflows/authored.yml"}}},
                    "concrete": {"location": {"start_point": {"row": 11}}}
                  }
                ]
              },
              {
                "ident": "unredacted-secrets",
                "desc": "non SEC-002 finding",
                "url": "https://docs.zizmor.sh/audits/#unredacted-secrets",
                "determinations": {"severity": "High"},
                "locations": [
                  {
                    "symbolic": {"kind": "Primary", "key": {"Local": {"given_path": ".github/workflows/authored.yml"}}},
                    "concrete": {"location": {"start_point": {"row": 8}}}
                  }
                ]
              }
            ]
            JSON
            """
        ),
        encoding="utf-8",
    )
    os.chmod(fake_bin / "zizmor", 0o755)

    env = os.environ.copy()
    env["PATH"] = f"{fake_bin}:{env['PATH']}"
    env["TMPDIR"] = str(tmp_path)

    result = subprocess.run(
        ["bash", str(SCRIPT), str(repo_root), "secrets"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )

    assert result.returncode == 0, result.stderr

    findings = [line for line in result.stdout.strip().splitlines() if line]
    assert any(
        line.startswith(".github/workflows/authored.yml|12|SEC-002|")
        for line in findings
    )
    assert not any(
        "generated.lock.yml" in line and "|SEC-002|" in line for line in findings
    )
    assert not any(
        line.startswith(".github/workflows/authored.yml|9|SEC-002|")
        for line in findings
    )
    assert any("|SEC-021|" in line for line in findings)
