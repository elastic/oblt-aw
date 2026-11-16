"""Tests for scripts/validate_docs_terminology.py."""

from __future__ import annotations

import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import validate_docs_terminology as validator


def _write_docs(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "docset.yml").write_text(
        textwrap.dedent(
            """
            exclude:
              - "**/README.md"
            toc:
              - file: guide.md
            """
        ).lstrip(),
        encoding="utf-8",
    )
    (docs / "guide.md").write_text(body, encoding="utf-8")
    return docs


def test_rejects_control_plane_owns_runtime(tmp_path: pathlib.Path) -> None:
    docs = _write_docs(
        tmp_path,
        "Bring your own behavior while the control plane still owns "
        "runtime, locks, and schedule clients.\n",
    )
    errors = validator.find_terminology_errors(
        docs_dir=docs, docset_path=docs / "docset.yml"
    )
    assert errors
    assert "guide.md:1:" in errors[0]


def test_allows_framework_owns_and_control_plane_gates(
    tmp_path: pathlib.Path,
) -> None:
    docs = _write_docs(
        tmp_path,
        "The framework owns runtime, locks, and schedule clients; the "
        "control plane (Control Plane dashboard and prelude) only enables "
        "or gates those agentic workflows.\n",
    )
    errors = validator.find_terminology_errors(
        docs_dir=docs, docset_path=docs / "docset.yml"
    )
    assert errors == []


def test_ignores_fenced_code_examples(tmp_path: pathlib.Path) -> None:
    docs = _write_docs(
        tmp_path,
        textwrap.dedent(
            """
            Prose is fine.

            ```text
            while the control plane still owns runtime
            ```
            """
        ).lstrip(),
    )
    errors = validator.find_terminology_errors(
        docs_dir=docs, docset_path=docs / "docset.yml"
    )
    assert errors == []
