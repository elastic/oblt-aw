"""Tests for scripts/validate_aw_workflow_checkout_persist_credentials.py."""

from __future__ import annotations

import pathlib
import sys

import yaml

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import validate_aw_workflow_checkout_persist_credentials as validator


def _write_workflow(path: pathlib.Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_validate_workflow_rejects_checkout_without_persist_credentials(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    workflow_path = workflows / "sample.yml"
    _write_workflow(
        workflow_path,
        {
            "name": "Sample",
            "on": {"workflow_dispatch": None},
            "jobs": {
                "build": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {"name": "Checkout", "uses": "actions/checkout@v7.0.1"},
                    ],
                }
            },
        },
    )

    errors = validator.validate_workflow_file(workflow_path)
    assert len(errors) == 1
    assert "persist-credentials: false" in errors[0]


def test_validate_workflow_accepts_checkout_with_persist_credentials_false(
    tmp_path: pathlib.Path,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)

    workflow_path = workflows / "sample.yml"
    _write_workflow(
        workflow_path,
        {
            "name": "Sample",
            "on": {"workflow_dispatch": None},
            "jobs": {
                "build": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout",
                            "uses": "actions/checkout@v7.0.1",
                            "with": {"persist-credentials": False},
                        },
                    ],
                }
            },
        },
    )

    assert validator.validate_workflow_file(workflow_path) == []


def test_list_workflow_files_excludes_lock_files_in_main(
    tmp_path: pathlib.Path,
    monkeypatch: object,
) -> None:
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    _write_workflow(
        workflows / "regular.yml",
        {"name": "Regular", "on": {"workflow_dispatch": None}, "jobs": {}},
    )
    _write_workflow(
        workflows / "generated.lock.yml",
        {"name": "Generated", "on": {"workflow_dispatch": None}, "jobs": {}},
    )

    monkeypatch.setattr(validator, "WORKFLOWS_DIR", workflows)
    listed = validator.list_workflow_files()
    assert {p.name for p in listed} == {"generated.lock.yml", "regular.yml"}
