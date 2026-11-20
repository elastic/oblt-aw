"""Tests for scripts/sync_python_version.py."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import sync_python_version as syncer


def test_load_python_version(tmp_path: pathlib.Path) -> None:
    pin = tmp_path / ".python-version"
    pin.write_text("3.14\n", encoding="utf-8")
    assert syncer.load_python_version(pin) == "3.14"


def test_apply_runtime_setup_replaces_consumer_file(
    tmp_path: pathlib.Path,
) -> None:
    text = (
        "---\nsteps:\n"
        "  - name: Setup Python\n"
        "    if: hashFiles('.python-version') != ''\n"
        "    uses: actions/setup-python@v7\n"
        "    with:\n"
        "      python-version-file: '.python-version'\n"
        "\n"
        "  - name: Setup Node.js (.node-version)\n"
        "    uses: actions/setup-node@v7\n"
    )
    out = syncer.apply_runtime_setup(text, "3.14")
    assert "python-version-file:" not in out
    assert "python-version: '3.14'" in out
    assert syncer.BEGIN_RUNTIME in out
    assert "Setup Node.js" in out


def test_apply_obs_defaults_inserts_runtimes() -> None:
    text = (
        "---\n"
        "model: gpt-5.3-codex\n"
        "tools:\n"
        "  github:\n"
        '    trusted-users: "github-actions[bot]"\n'
        "---\n\n"
        "## Observability defaults\n"
    )
    out = syncer.apply_obs_defaults(text, "3.14")
    assert 'version: "3.14"' in out
    assert syncer.BEGIN_RUNTIMES in out
    # Idempotent when markers already present.
    again = syncer.apply_obs_defaults(out, "3.15")
    assert 'version: "3.15"' in again
    assert again.count(syncer.BEGIN_RUNTIMES) == 1


def test_validate_control_plane_requires_version_file(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    bad = workflows / "example.yml"
    bad.write_text(
        "jobs:\n"
        "  t:\n"
        "    steps:\n"
        "      - uses: actions/setup-python@v7\n"
        "        with:\n"
        '          python-version: "3.14"\n',
        encoding="utf-8",
    )
    errors = syncer.validate_control_plane_setup_python(workflows)
    assert errors
    assert "python-version-file" in errors[0]


def test_validate_locks_reject_consumer_file(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / "workflows"
    workflows.mkdir()
    lock = workflows / "gh-aw-example.lock.yml"
    lock.write_text(
        "jobs:\n"
        "  agent:\n"
        "    steps:\n"
        "      - name: Setup Python\n"
        "        uses: actions/setup-python@v7\n"
        "        with:\n"
        "          python-version-file: .python-version\n",
        encoding="utf-8",
    )
    errors = syncer.validate_locks_use_control_plane_pin("3.14", workflows)
    assert any("delegates" in err for err in errors)


def test_repo_pins_match_python_version() -> None:
    """Live fragments/locks must stay aligned with root .python-version."""
    root = pathlib.Path(__file__).resolve().parents[2]
    version = syncer.load_python_version(root / ".python-version")
    # Temporarily point module paths are already ROOT-relative via imports;
    # run check against the real worktree by invoking check().
    errors = syncer.check(version)
    assert errors == [], errors
