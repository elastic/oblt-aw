"""Tests for scripts/sync_allowed_pr_authors_bots.py."""

from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import sync_allowed_pr_authors_bots as sync

_AUTHORS = [
    "dependabot[bot]",
    "renovate[bot]",
    "github-actions[bot]",
]


def _sample_source(*, with_prompt: bool) -> str:
    bots = sync.render_bots_block(_AUTHORS)
    trusted = sync.render_trusted_block(_AUTHORS)
    parts = [
        "---\n",
        "on:\n",
        "  workflow_call: {}\n",
        "  roles: [admin, maintainer, write]\n",
        bots,
        "concurrency:\n",
        "  group: test\n",
        "tools:\n",
        "  github:\n",
        "    github-token: ${{ secrets.GITHUB_TOKEN }}\n",
        trusted,
        "\n",
        "    toolsets: [repos]\n",
    ]
    if with_prompt:
        parts.extend(
            [
                "---\n\n",
                "## Author allow list\n\n",
                (
                    "Canonical list (from `config/obs/allowed_pr_authors.json`"
                    " — do not invent other names):\n\n"
                ),
                sync.render_prompt_bullets(_AUTHORS),
                "\n",
                "Read the PR author via GitHub MCP.\n",
            ]
        )
    return "".join(parts)


def test_render_blocks_match_authors() -> None:
    bots = sync.render_bots_block(_AUTHORS)
    trusted = sync.render_trusted_block(_AUTHORS)
    prompt = sync.render_prompt_bullets(_AUTHORS)
    assert '    - "renovate[bot]"' in bots
    assert bots.startswith(sync.BEGIN_BOTS)
    assert trusted.startswith(sync.BEGIN_TRUSTED)
    assert (
        'trusted-users: "dependabot[bot],renovate[bot],github-actions[bot]"' in trusted
    )
    assert trusted.endswith(sync.END_TRUSTED)
    assert prompt == (
        "- `dependabot[bot]`\n- `renovate[bot]`\n- `github-actions[bot]`\n"
    )


def test_sync_file_is_idempotent(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "gh-aw-autoapprove.md"
    path.write_text(_sample_source(with_prompt=True), encoding="utf-8")
    once = sync.sync_file(path, _AUTHORS, with_prompt=True)
    path.write_text(once, encoding="utf-8")
    twice = sync.sync_file(path, _AUTHORS, with_prompt=True)
    assert once == twice


def test_sync_file_updates_when_authors_change(tmp_path: pathlib.Path) -> None:
    path = tmp_path / "wf.md"
    path.write_text(_sample_source(with_prompt=True), encoding="utf-8")
    updated = sync.sync_file(
        path,
        [*_AUTHORS, "mergify[bot]"],
        with_prompt=True,
    )
    assert '    - "mergify[bot]"' in updated
    assert "- `mergify[bot]`" in updated
    assert "mergify[bot]" in updated.split("trusted-users:")[1]


def test_load_authors_reads_repo_json() -> None:
    authors = sync.load_authors()
    expected = json.loads(sync.ALLOW_JSON.read_text(encoding="utf-8"))
    assert authors == expected
