"""Focused tests for scripts/obs/security-scan.sh secret rule mapping."""

from __future__ import annotations

import os
import pathlib
import stat
import subprocess
import textwrap

SCRIPT = (
    pathlib.Path(__file__).resolve().parents[2] / "scripts" / "obs" / "security-scan.sh"
)


def _write_executable(path: pathlib.Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _prepare_fake_tooling(
    tmp_path: pathlib.Path, workflow_path: pathlib.Path
) -> pathlib.Path:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    # Keep SEC-002 signal deterministic in tests by no-oping optional analyzers.
    _write_executable(
        bin_dir / "actionlint",
        "#!/usr/bin/env bash\nprintf '[]\n'",
    )
    _write_executable(
        bin_dir / "semgrep",
        "#!/usr/bin/env bash\nprintf '{\"results\":[]}\n'",
    )

    # Emit one zizmor secrets-outside-env finding and assert mapping is not SEC-002.
    _write_executable(
        bin_dir / "zizmor",
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            cat <<'JSON'
            [{{
              "ident": "secrets-outside-env",
              "desc": "secrets referenced without a dedicated environment",
              "url": "https://docs.zizmor.sh/audits/#secrets-outside-env",
              "determinations": {{"severity": "Medium"}},
              "locations": [{{
                "symbolic": {{
                  "kind": "Primary",
                  "key": {{"Local": {{"given_path": "{workflow_path}"}}}}
                }},
                "concrete": {{"location": {{"start_point": {{"row": 5}}}}}}
              }}]
            }}]
            JSON
            """
        ),
    )
    return bin_dir


def _run_scan(
    repo_root: pathlib.Path, bin_dir: pathlib.Path
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env['PATH']}"
    return subprocess.run(
        ["bash", str(SCRIPT), str(repo_root), "secrets"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_sec_002_detects_inline_and_block_run_secret_interpolation(
    tmp_path: pathlib.Path,
) -> None:
    repo_root = tmp_path / "repo"
    workflow_dir = repo_root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow_path = workflow_dir / "scan.yml"
    workflow_path.write_text(
        textwrap.dedent(
            """\
            name: test
            on: push
            jobs:
              sec:
                runs-on: ubuntu-latest
                steps:
                  - run: echo "${{ secrets.GITHUB_TOKEN }}"
                  - run: |
                      echo "safe"
                      curl -H "Authorization: ${{ secrets.API_TOKEN }}" https://example.invalid
            """
        ),
        encoding="utf-8",
    )
    bin_dir = _prepare_fake_tooling(tmp_path, workflow_path)
    result = _run_scan(repo_root, bin_dir)

    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.strip().splitlines() if line]
    sec_002 = [line for line in lines if "|SEC-002|" in line]
    assert len(sec_002) == 2
    assert all(line.startswith(".github/workflows/scan.yml|") for line in sec_002)
    assert all("|high|" in line for line in sec_002)


def test_sec_002_does_not_include_zizmor_secrets_outside_env(
    tmp_path: pathlib.Path,
) -> None:
    repo_root = tmp_path / "repo"
    workflow_dir = repo_root / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    workflow_path = workflow_dir / "scan.yml"
    workflow_path.write_text(
        textwrap.dedent(
            """\
            name: test
            on: push
            jobs:
              sec:
                runs-on: ubuntu-latest
                env:
                  GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
                steps:
                  - run: echo "ok"
            """
        ),
        encoding="utf-8",
    )
    bin_dir = _prepare_fake_tooling(tmp_path, workflow_path)
    result = _run_scan(repo_root, bin_dir)

    assert result.returncode == 0, result.stderr
    lines = [line for line in result.stdout.strip().splitlines() if line]
    assert not any("|SEC-002|" in line for line in lines)
    assert any("|SEC-022|" in line for line in lines)
