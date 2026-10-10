"""Unit tests for scripts/obs/security-scan.sh SEC-002 behavior."""

from __future__ import annotations

import os
import pathlib
import subprocess
import textwrap

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _run_scan(repo_root: pathlib.Path, env: dict[str, str] | None = None) -> str:
    merged_env = os.environ.copy()
    merged_env["TMPDIR"] = "/tmp/gh-aw/agent"
    if env:
        merged_env.update(env)

    result = subprocess.run(
        ["bash", str(SCRIPT), str(repo_root), "secrets"],
        check=False,
        capture_output=True,
        text=True,
        env=merged_env,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def test_sec002_reports_source_workflow_run_secret_and_ignores_lock_files(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    (workflows / "source.yml").write_text(
        textwrap.dedent(
            """
            name: source
            on: workflow_dispatch
            jobs:
              sample:
                runs-on: ubuntu-latest
                steps:
                  - run: echo "${{ secrets.DEMO_TOKEN }}"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )
    (workflows / "generated.lock.yml").write_text(
        textwrap.dedent(
            """
            name: generated
            on: workflow_dispatch
            jobs:
              sample:
                runs-on: ubuntu-latest
                steps:
                  - run: echo "${{ secrets.DEMO_TOKEN }}"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    out = _run_scan(tmp_path)
    sec002_lines = [line for line in out.splitlines() if "|SEC-002|" in line]
    assert any(
        line.startswith(".github/workflows/source.yml|") for line in sec002_lines
    )
    assert not any("generated.lock.yml" in line for line in sec002_lines)


def test_sec002_does_not_emit_from_zizmor_secrets_outside_env_only(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    (workflows / "source.yml").write_text(
        textwrap.dedent(
            """
            name: source
            on: workflow_dispatch
            jobs:
              sample:
                runs-on: ubuntu-latest
                env:
                  GH_TOKEN: ${{ secrets.DEMO_TOKEN }}
                steps:
                  - run: echo "safe"
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    (fake_bin / "zizmor").write_text(
        textwrap.dedent(
            """#!/usr/bin/env bash
            cat <<'JSON'
            [
              {
                "ident": "secrets-outside-env",
                "desc": "secrets referenced without a dedicated environment",
                "url": "https://docs.zizmor.sh/audits/#secrets-outside-env",
                "determinations": { "severity": "medium" },
                "locations": [
                  {
                    "symbolic": {
                      "kind": "Primary",
                      "key": {
                        "Local": { "given_path": ".github/workflows/source.yml" }
                      }
                    },
                    "concrete": { "location": { "start_point": { "row": 4 } } }
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

    out = _run_scan(tmp_path, env={"PATH": f"{fake_bin}:{os.environ['PATH']}"})
    assert "|SEC-002|" not in out
