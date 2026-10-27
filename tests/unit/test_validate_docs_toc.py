"""Tests for scripts/validate_docs_toc.py."""

from __future__ import annotations

import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import validate_docs_toc as validator


def _write_docset(tmp_path: pathlib.Path, body: str) -> pathlib.Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    path = docs / "docset.yml"
    path.write_text(textwrap.dedent(body).lstrip(), encoding="utf-8")
    return docs


def test_collect_toc_paths_nested_hidden_and_file() -> None:
    toc = [
        {"file": "index.md"},
        {
            "folder": "workflows",
            "children": [
                {"hidden": "./gh-aw-autoapprove.md"},
                {"file": "obs-aw-automerge.md"},
            ],
        },
    ]
    assert validator.collect_toc_paths(toc) == {
        "index.md",
        "workflows/gh-aw-autoapprove.md",
        "workflows/obs-aw-automerge.md",
    }


def test_is_excluded_readme_and_fixture_globs() -> None:
    patterns = ["**/README.md", "testing/fixtures/**", "examples/**"]
    assert validator.is_excluded("README.md", patterns)
    assert validator.is_excluded("onboarding/README.md", patterns)
    assert validator.is_excluded("testing/fixtures/e2e-autodoc-bait.md", patterns)
    assert validator.is_excluded("examples/foo.md", patterns)
    assert not validator.is_excluded("workflows/gh-aw-autoapprove.md", patterns)


def test_validate_docset_reports_missing_toc_entry(tmp_path: pathlib.Path) -> None:
    docs = _write_docset(
        tmp_path,
        """
        exclude:
          - "**/README.md"
        toc:
          - file: index.md
        """,
    )
    (docs / "index.md").write_text("# Home\n", encoding="utf-8")
    (docs / "orphan.md").write_text("# Orphan\n", encoding="utf-8")

    errors = validator.validate_docset(docs_dir=docs, docset_path=docs / "docset.yml")
    assert len(errors) == 1
    assert "orphan.md" in errors[0]
    assert "missing from docs/docset.yml toc" in errors[0]


def test_validate_docset_reports_orphan_toc_entry(tmp_path: pathlib.Path) -> None:
    docs = _write_docset(
        tmp_path,
        """
        exclude: []
        toc:
          - file: index.md
          - file: gone.md
        """,
    )
    (docs / "index.md").write_text("# Home\n", encoding="utf-8")

    errors = validator.validate_docset(docs_dir=docs, docset_path=docs / "docset.yml")
    assert len(errors) == 1
    assert "gone.md" in errors[0]


def test_validate_docset_ignores_excluded_readme(tmp_path: pathlib.Path) -> None:
    docs = _write_docset(
        tmp_path,
        """
        exclude:
          - "**/README.md"
        toc:
          - file: index.md
        """,
    )
    (docs / "index.md").write_text("# Home\n", encoding="utf-8")
    (docs / "README.md").write_text("# Repo readme\n", encoding="utf-8")

    assert (
        validator.validate_docset(docs_dir=docs, docset_path=docs / "docset.yml") == []
    )


def test_repo_docset_is_complete() -> None:
    """Live docs/ tree must stay toc-complete (Codex preview gate)."""
    assert validator.validate_docset() == []
