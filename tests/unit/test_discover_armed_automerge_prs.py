"""Regression tests for scripts/obs/discover_armed_automerge_prs.sh."""

from __future__ import annotations

import base64
import json
import os
import pathlib
import re
import subprocess
import textwrap

ROOT = pathlib.Path(__file__).resolve().parents[2]
DISCOVER = ROOT / "scripts" / "obs" / "discover_armed_automerge_prs.sh"

_DEFAULT_BASE = "d" * 40
_RELEASE_BASE = "r" * 40
_MERGE_READY = "oblt-aw/ai/merge-ready"
_CUSTOM = "nightshift:risk-low"
_BOT = "github-actions[bot]"


def _sha_for_pr(pr: int) -> str:
    return f"{pr:040x}"


def _apm_b64(*, custom: bool) -> str:
    if custom:
        body = (
            "workflows:\n"
            "  automerge:\n"
            "    policy:\n"
            f"      trigger-labels: [{_CUSTOM!r}]\n"
        )
    else:
        body = "workflows: {}\n"
    return base64.b64encode(body.encode()).decode()


def _install_fake_oblt_root(tmp_path: pathlib.Path) -> pathlib.Path:
    """Stub resolver that reads trigger markers from REPO_ROOT/apm.yml."""
    root = tmp_path / "oblt-aw"
    scripts = root / "scripts"
    scripts.mkdir(parents=True)
    (scripts / "resolve_automerge_policy_cli.py").write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json, os, pathlib
            repo = pathlib.Path(os.environ.get("REPO_ROOT", ".")).resolve()
            apm = repo / "apm.yml"
            text = apm.read_text(encoding="utf-8") if apm.is_file() else ""
            if {_CUSTOM!r} in text:
                triggers = [{_CUSTOM!r}, {_MERGE_READY!r}]
            else:
                triggers = [{_MERGE_READY!r}]
            payload = json.dumps(
                {{"trigger-labels": triggers}},
                separators=(",", ":"),
                sort_keys=True,
            )
            out = os.environ.get("GITHUB_OUTPUT")
            if out:
                with open(out, "a", encoding="utf-8") as fh:
                    fh.write("automerge-policy-json=" + payload + "\\n")
            print(payload)
            """
        ),
        encoding="utf-8",
    )
    return root


def _install_fake_gh(
    tmp_path: pathlib.Path,
    *,
    pulls: list[dict[str, object]],
    labels_by_pr: dict[int, list[str]],
    base_by_pr: dict[int, str],
) -> dict[str, str]:
    state = {
        "pulls": pulls,
        "labels": {str(k): v for k, v in labels_by_pr.items()},
        "bases": {str(k): v for k, v in base_by_pr.items()},
        "default_apm": _apm_b64(custom=False),
        "release_apm": _apm_b64(custom=True),
        "release_base": _RELEASE_BASE,
        "bot": _BOT,
    }
    state_path = tmp_path / "fake_gh_state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")

    gh_py = tmp_path / "fake_gh.py"
    gh_py.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env python3
            import json, re, sys
            state = json.loads(open({str(state_path)!r}, encoding="utf-8").read())
            args = sys.argv[1:]
            joined = " ".join(args)

            if "pulls?state=open" in joined:
                for p in state["pulls"]:
                    sha = (p.get("head") or {{}}).get("sha")
                    if sha:
                        print(f"{{p['number']}}\\t{{sha}}")
                raise SystemExit(0)

            m = re.search(r"issues/(\\d+)/comments", joined)
            if m:
                pr = m.group(1)
                match = next(p for p in state["pulls"] if str(p["number"]) == pr)
                sha = match["head"]["sha"]
                print(json.dumps([{{
                    "id": 1,
                    "user": {{"login": state["bot"]}},
                    "body": (
                        f"armed\\n<!-- obs-aw-automerge:armed sha={{sha}} -->\\n"
                    ),
                }}]))
                raise SystemExit(0)

            m = re.search(r"pulls/(\\d+)", joined)
            if m and "--jq" in args and ".base.sha" in joined:
                print(state["bases"][m.group(1)])
                raise SystemExit(0)

            if m and "--jq" in args and ".labels" in joined:
                print(json.dumps(state["labels"][m.group(1)]))
                raise SystemExit(0)

            if "/contents/apm.yml" in joined or "/contents/apm.yaml" in joined:
                content = state["default_apm"]
                if f"ref={{state['release_base']}}" in joined:
                    content = state["release_apm"]
                print(json.dumps({{"content": content}}))
                raise SystemExit(0)

            print(f"unexpected gh args: {{joined}}", file=sys.stderr)
            raise SystemExit(99)
            """
        ),
        encoding="utf-8",
    )
    gh_py.chmod(0o755)

    wrapper = tmp_path / "gh"
    wrapper.write_text(
        textwrap.dedent(
            f"""\
            #!/usr/bin/env bash
            exec python3 {str(gh_py)!r} "$@"
            """
        ),
        encoding="utf-8",
    )
    wrapper.chmod(0o755)

    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}{os.pathsep}{env['PATH']}"
    env["GH_TOKEN"] = "test-token"
    env["GITHUB_REPOSITORY"] = "owner/repo"
    return env


def _run_discover(
    tmp_path: pathlib.Path,
    env: dict[str, str],
    *,
    run_number: str = "0",
    max_candidates: str = "100",
    oblt_root: pathlib.Path | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    out_file = tmp_path / f"github_output_{run_number}"
    out_file.write_text("", encoding="utf-8")
    run_env = env.copy()
    run_env["GITHUB_OUTPUT"] = str(out_file)
    run_env["GITHUB_RUN_NUMBER"] = run_number
    run_env["AUTOMERGE_DISCOVER_MAX_CANDIDATES"] = max_candidates
    run_env["POLICY_CACHE_DIR"] = str(tmp_path / f"policy-cache-{run_number}")
    if oblt_root is None:
        run_env.pop("OBLT_AW_ROOT", None)
    else:
        run_env["OBLT_AW_ROOT"] = str(oblt_root)
    result = subprocess.run(
        ["bash", str(DISCOVER)],
        capture_output=True,
        text=True,
        check=False,
        env=run_env,
    )
    outputs: dict[str, str] = {}
    text = out_file.read_text(encoding="utf-8")
    if "candidates<<EOF" in text:
        body = text.split("candidates<<EOF\n", 1)[1].split("\nEOF\n", 1)[0]
        outputs["candidates"] = body
    for line in text.splitlines():
        if line.startswith("has-candidates="):
            outputs["has-candidates"] = line.split("=", 1)[1]
    return result, outputs


def _fixture_world() -> tuple[
    list[dict[str, object]],
    dict[int, list[str]],
    dict[int, str],
]:
    """110 merge-ready + 6 opted-out + 1 release custom-trigger PR."""
    pulls: list[dict[str, object]] = []
    labels: dict[int, list[str]] = {}
    bases: dict[int, str] = {}

    for n in range(1, 111):
        pulls.append({"number": n, "head": {"sha": _sha_for_pr(n)}})
        labels[n] = [_MERGE_READY]
        bases[n] = _DEFAULT_BASE

    for n in range(200, 206):
        pulls.append({"number": n, "head": {"sha": _sha_for_pr(n)}})
        labels[n] = []
        bases[n] = _DEFAULT_BASE

    pulls.append({"number": 999, "head": {"sha": _sha_for_pr(999)}})
    labels[999] = [_CUSTOM]
    bases[999] = _RELEASE_BASE
    return pulls, labels, bases


def test_discover_legacy_path_without_oblt_root(tmp_path: pathlib.Path) -> None:
    """@v0 sparse fetch: no OBLT_AW_ROOT → merge-ready-only, no hard fail."""
    pulls = [
        {"number": 1, "head": {"sha": _sha_for_pr(1)}},
        {"number": 2, "head": {"sha": _sha_for_pr(2)}},
    ]
    labels = {1: [_MERGE_READY], 2: [_CUSTOM]}
    bases = {1: _DEFAULT_BASE, 2: _RELEASE_BASE}
    env = _install_fake_gh(tmp_path, pulls=pulls, labels_by_pr=labels, base_by_pr=bases)
    result, outputs = _run_discover(tmp_path, env, oblt_root=None)
    assert result.returncode == 0, result.stderr
    assert "merge-ready-only legacy path" in result.stderr
    candidates = json.loads(outputs["candidates"])
    assert [c["pr_number"] for c in candidates] == ["1"]
    assert outputs["has-candidates"] == "true"


def test_discover_cap_rotation_opt_out_and_per_base_policy(
    tmp_path: pathlib.Path,
) -> None:
    """Opted-out PRs skip the cap; release custom trigger stays eligible; run rotates."""
    pulls, labels, bases = _fixture_world()
    env = _install_fake_gh(tmp_path, pulls=pulls, labels_by_pr=labels, base_by_pr=bases)
    oblt_root = _install_fake_oblt_root(tmp_path)

    first, out0 = _run_discover(
        tmp_path, env, run_number="0", max_candidates="100", oblt_root=oblt_root
    )
    assert first.returncode == 0, first.stderr + first.stdout
    c0 = json.loads(out0["candidates"])
    nums0 = [int(c["pr_number"]) for c in c0]
    assert len(nums0) == 100
    assert nums0 == list(range(1, 101))
    assert 999 not in nums0
    assert all(n < 200 or n > 205 for n in nums0)

    second, out1 = _run_discover(
        tmp_path, env, run_number="1", max_candidates="100", oblt_root=oblt_root
    )
    assert second.returncode == 0, second.stderr + second.stdout
    c1 = json.loads(out1["candidates"])
    nums1 = [int(c["pr_number"]) for c in c1]
    assert len(nums1) == 100
    assert 999 in nums1
    assert set(range(200, 206)).isdisjoint(nums1)
    assert set(nums1) - set(nums0)
    assert re.search(r"\b111 eligible\b", first.stdout + second.stdout)
