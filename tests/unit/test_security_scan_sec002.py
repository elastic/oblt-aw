"""Regression tests for SEC-002 filtering in scripts/obs/security-scan.sh."""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import tempfile

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _write(path: pathlib.Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _fake_zizmor_payload(repo_root: pathlib.Path) -> str:
    authored = repo_root / ".github" / "workflows" / "authored.yml"
    generated = repo_root / ".github" / "workflows" / "generated.lock.yml"
    findings = [
        {
            "ident": "secrets-outside-env",
            "desc": "env secret in generated lock workflow",
            "url": "https://example.test/zizmor/secrets-outside-env",
            "determinations": {"severity": "Medium"},
            "locations": [
                {
                    "symbolic": {
                        "kind": "Primary",
                        "key": {"Local": {"given_path": str(generated)}},
                    },
                    "concrete": {"location": {"start_point": {"row": 7}}},
                }
            ],
        },
        {
            "ident": "secrets-outside-env",
            "desc": "env secret in authored workflow",
            "url": "https://example.test/zizmor/secrets-outside-env",
            "determinations": {"severity": "Medium"},
            "locations": [
                {
                    "symbolic": {
                        "kind": "Primary",
                        "key": {"Local": {"given_path": str(authored)}},
                    },
                    "concrete": {"location": {"start_point": {"row": 7}}},
                }
            ],
        },
        {
            "ident": "secrets-outside-env",
            "desc": "secret in run command",
            "url": "https://example.test/zizmor/secrets-outside-env",
            "determinations": {"severity": "Medium"},
            "locations": [
                {
                    "symbolic": {
                        "kind": "Primary",
                        "key": {"Local": {"given_path": str(authored)}},
                    },
                    "concrete": {"location": {"start_point": {"row": 10}}},
                }
            ],
        },
        {
            "ident": "unpinned-uses",
            "desc": "unpinned action reference",
            "url": "https://example.test/zizmor/unpinned-uses",
            "determinations": {"severity": "High"},
            "locations": [
                {
                    "symbolic": {
                        "kind": "Primary",
                        "key": {"Local": {"given_path": str(generated)}},
                    },
                    "concrete": {"location": {"start_point": {"row": 3}}},
                }
            ],
        },
    ]
    return json.dumps(findings)


def _run_scan(
    repo_root: pathlib.Path, category: str | None
) -> subprocess.CompletedProcess[str]:
    with tempfile.TemporaryDirectory(
        prefix="zizmor-bin-", dir="/tmp/gh-aw/agent"
    ) as tool_dir:
        tool_path = pathlib.Path(tool_dir) / "zizmor"
        payload = _fake_zizmor_payload(repo_root).replace("'", "'\"'\"'")
        tool_path.write_text(
            f"#!/usr/bin/env bash\nset -euo pipefail\ncat <<'JSON'\n{payload}\nJSON\n",
            encoding="utf-8",
        )
        tool_path.chmod(0o755)

        cmd = ["bash", str(SCRIPT), str(repo_root)]
        if category:
            cmd.append(category)
        env = {
            **os.environ,
            "PATH": f"{tool_dir}:{os.environ.get('PATH', '')}",
            "TMPDIR": "/tmp/gh-aw/agent",
        }
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            env=env,
        )


def _prepare_repo(repo_root: pathlib.Path) -> None:
    _write(
        repo_root / ".github" / "workflows" / "generated.lock.yml",
        """name: generated
jobs:
  demo:
    uses: owner/repo/.github/workflows/reusable.yml@main
    runs-on: ubuntu-latest
    steps:
      - name: generated env
        env:
          TOKEN: ${{ secrets.GENERATED_TOKEN }}
        run: echo "generated"
""",
    )
    _write(
        repo_root / ".github" / "workflows" / "authored.yml",
        """name: authored
jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - name: authored env
        env:
          TOKEN: ${{ secrets.ENV_TOKEN }}
        run: echo "safe"
      - name: authored run
        run: echo "${{ secrets.RUN_TOKEN }}"
""",
    )


def test_sec002_keeps_only_authored_run_context_in_secrets_category() -> None:
    with tempfile.TemporaryDirectory(
        prefix="sec002-repo-", dir="/tmp/gh-aw/agent"
    ) as tmp:
        repo_root = pathlib.Path(tmp)
        _prepare_repo(repo_root)
        result = _run_scan(repo_root, "secrets")

    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert lines == [
        ".github/workflows/authored.yml|11|SEC-002|medium|zizmor [secrets-outside-env]: secret in run command (https://example.test/zizmor/secrets-outside-env)"
    ]


def test_sec002_filter_does_not_affect_non_sec002_findings() -> None:
    with tempfile.TemporaryDirectory(
        prefix="sec002-repo-", dir="/tmp/gh-aw/agent"
    ) as tmp:
        repo_root = pathlib.Path(tmp)
        _prepare_repo(repo_root)
        result = _run_scan(repo_root, None)

    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    assert (
        ".github/workflows/authored.yml|11|SEC-002|medium|zizmor [secrets-outside-env]: secret in run command (https://example.test/zizmor/secrets-outside-env)"
        in lines
    )
    assert (
        ".github/workflows/generated.lock.yml|4|SEC-030|medium|zizmor [unpinned-uses]: unpinned action reference (https://example.test/zizmor/unpinned-uses)"
        in lines
    )
