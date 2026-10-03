"""Tests for scripts/validate_aw_workflow_checkout_persist_credentials.py."""

from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import validate_aw_workflow_checkout_persist_credentials as validator


def test_rejects_checkout_without_with_block(tmp_path: pathlib.Path) -> None:
    workflow = tmp_path / "missing-with.yml"
    workflow.write_text(
        "name: Test\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/checkout@v7\n",
        encoding="utf-8",
    )
    errors, count = validator.validate_workflow(workflow)
    assert count == 1
    assert len(errors) == 1
    assert "persist-credentials: false" in errors[0]


def test_rejects_checkout_missing_persist_credentials(tmp_path: pathlib.Path) -> None:
    workflow = tmp_path / "missing-persist.yml"
    workflow.write_text(
        "name: Test\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/checkout@v7\n"
        "        with:\n"
        "          fetch-depth: 1\n",
        encoding="utf-8",
    )
    errors, _ = validator.validate_workflow(workflow)
    assert len(errors) == 1
    assert "persist-credentials: false" in errors[0]


def test_rejects_persist_credentials_true(tmp_path: pathlib.Path) -> None:
    workflow = tmp_path / "persist-true.yml"
    workflow.write_text(
        "name: Test\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/checkout@v7\n"
        "        with:\n"
        "          persist-credentials: true\n",
        encoding="utf-8",
    )
    errors, _ = validator.validate_workflow(workflow)
    assert len(errors) == 1
    assert "non-false value" in errors[0]


def test_accepts_persist_credentials_false(tmp_path: pathlib.Path) -> None:
    workflow = tmp_path / "persist-false.yml"
    workflow.write_text(
        "name: Test\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/checkout@v7\n"
        "        with:\n"
        "          persist-credentials: false\n",
        encoding="utf-8",
    )
    errors, count = validator.validate_workflow(workflow)
    assert count == 1
    assert errors == []


def test_accepts_pinned_checkout_with_inline_comments(tmp_path: pathlib.Path) -> None:
    workflow = tmp_path / "pinned-with-comment.yml"
    workflow.write_text(
        "name: Test\njobs:\n  t:\n    runs-on: ubuntu-latest\n    steps:\n"
        "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1"
        " # v7.0.1\n"
        "        with:\n"
        "          persist-credentials: false # required by SEC-031\n",
        encoding="utf-8",
    )
    errors, count = validator.validate_workflow(workflow)
    assert count == 1
    assert errors == []


def test_main_passes_on_repo_workflows() -> None:
    assert validator.main() == 0
