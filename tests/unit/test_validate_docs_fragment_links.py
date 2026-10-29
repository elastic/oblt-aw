"""Tests for scripts/validate_docs_fragment_links.py."""

from __future__ import annotations

import pathlib
import sys
import textwrap

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import validate_docs_fragment_links as validator


def _write_docs(tmp_path: pathlib.Path) -> pathlib.Path:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "docset.yml").write_text(
        textwrap.dedent(
            """
            exclude:
              - "**/README.md"
            toc:
              - file: index.md
              - file: architecture.md
              - file: guide.md
            """
        ).lstrip(),
        encoding="utf-8",
    )
    return docs


def test_slugify_keeps_period_in_numbered_heading() -> None:
    assert (
        validator.slugify_heading(
            "11. Common services (shared definitions, per-org catalogs)"
        )
        == "11.-common-services-shared-definitions-per-org-catalogs"
    )


def test_slugify_keeps_period_in_filename_style_heading() -> None:
    assert validator.slugify_heading("release-pointers.json") == (
        "release-pointers.json"
    )


def test_heading_anchors_include_custom_and_default() -> None:
    markdown = textwrap.dedent(
        """
        # Title

        ## 11. Common services (shared definitions, per-org catalogs) [common-services]
        """
    ).lstrip()
    anchors = validator.heading_anchors(markdown)
    assert "common-services" in anchors
    assert "11.-common-services-shared-definitions-per-org-catalogs" in anchors


def test_validate_reports_wrong_numbered_fragment_without_period(
    tmp_path: pathlib.Path,
) -> None:
    docs = _write_docs(tmp_path)
    (docs / "index.md").write_text("# Home\n", encoding="utf-8")
    (docs / "architecture.md").write_text(
        "## 11. Common services (shared definitions, per-org catalogs)\n",
        encoding="utf-8",
    )
    (docs / "guide.md").write_text(
        "See [§11](architecture.md#11-common-services-shared-definitions-per-org-catalogs)\n",
        encoding="utf-8",
    )

    errors = validator.validate_fragment_links(
        docs_dir=docs, docset_path=docs / "docset.yml"
    )
    assert len(errors) == 1
    assert "guide.md:1:" in errors[0]
    assert "`11-common-services-shared-definitions-per-org-catalogs`" in errors[0]


def test_validate_accepts_custom_anchor_link(tmp_path: pathlib.Path) -> None:
    docs = _write_docs(tmp_path)
    (docs / "index.md").write_text("# Home\n", encoding="utf-8")
    (docs / "architecture.md").write_text(
        "## 11. Common services (shared definitions, per-org catalogs) "
        "[common-services]\n",
        encoding="utf-8",
    )
    (docs / "guide.md").write_text(
        "See [§11](architecture.md#common-services)\n",
        encoding="utf-8",
    )

    assert (
        validator.validate_fragment_links(
            docs_dir=docs, docset_path=docs / "docset.yml"
        )
        == []
    )


def test_validate_accepts_period_preserving_default_slug(
    tmp_path: pathlib.Path,
) -> None:
    docs = _write_docs(tmp_path)
    (docs / "index.md").write_text("# Home\n", encoding="utf-8")
    (docs / "architecture.md").write_text(
        "## release-pointers.json\n",
        encoding="utf-8",
    )
    (docs / "guide.md").write_text(
        "See [pointers](architecture.md#release-pointers.json)\n",
        encoding="utf-8",
    )

    assert (
        validator.validate_fragment_links(
            docs_dir=docs, docset_path=docs / "docset.yml"
        )
        == []
    )


def test_repo_docs_fragment_links_are_valid() -> None:
    """Live docs/ tree must keep relative fragments resolvable."""
    assert validator.validate_fragment_links() == []
