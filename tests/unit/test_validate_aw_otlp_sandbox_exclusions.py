"""Tests for scripts/validate_aw_otlp_sandbox_exclusions.py."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import validate_aw_otlp_sandbox_exclusions as validator


def test_accepts_full_excludes(tmp_path: pathlib.Path) -> None:
    lock = tmp_path / "gh-aw-example.lock.yml"
    excludes = " ".join(
        f"--exclude-env {name}" for name in validator.REQUIRED_EXCLUDE_ENV
    )
    lock.write_text(
        f"run: awf --config x.json --env-all {excludes} --skip-pull\n",
        encoding="utf-8",
    )
    assert validator.validate_lock(lock) == []


def test_rejects_missing_all_headers_exclude(tmp_path: pathlib.Path) -> None:
    lock = tmp_path / "gh-aw-example.lock.yml"
    # Omit GH_AW_OTLP_ALL_HEADERS deliberately.
    lock.write_text(
        "run: awf --env-all --exclude-env GH_AW_OTLP_ENDPOINTS "
        "--exclude-env OTEL_EXPORTER_OTLP_ENDPOINT "
        "--exclude-env OTEL_EXPORTER_OTLP_HEADERS --skip-pull\n",
        encoding="utf-8",
    )
    errors = validator.validate_lock(lock)
    assert any("GH_AW_OTLP_ALL_HEADERS" in err for err in errors)


def test_skips_non_awf_locks(tmp_path: pathlib.Path) -> None:
    lock = tmp_path / "plain.lock.yml"
    lock.write_text("name: no awf here\n", encoding="utf-8")
    assert validator.validate_lock(lock) == []


def test_repo_locks_pass() -> None:
    """Owned locks with awf --env-all must carry 68811 OTLP excludes."""
    locks = validator.list_lock_workflows(
        pathlib.Path(__file__).resolve().parents[2] / ".github" / "workflows"
    )
    assert locks, "expected compiled lock workflows in the worktree"
    errors: list[str] = []
    for path in locks:
        text = path.read_text(encoding="utf-8")
        if "awf" not in text or "--env-all" not in text:
            continue
        errors.extend(validator.validate_lock_text(path, text))
    assert errors == []
