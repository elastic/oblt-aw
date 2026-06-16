"""
Unit tests for scripts/autodocignore.py and autodoc workflow integration.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root / "scripts"))

import agentic_assets_resolver as resolver  # noqa: E402
import autodocignore as adi  # noqa: E402


@pytest.fixture
def repo(tmp_path: pathlib.Path) -> pathlib.Path:
    return tmp_path


class TestParseAutodocignoreLines:
    def test_skips_blank_lines_and_comments(self) -> None:
        content = """
# ignore generated docs
docs/generated/

# another comment
*.lock
"""
        assert adi.parse_autodocignore_lines(content) == [
            "docs/generated/",
            "*.lock",
        ]


class TestPathMatchesAutodocignore:
    def test_matches_gitignore_style_patterns(self, repo: pathlib.Path) -> None:
        (repo / adi.AUTODOCIGNORE_FILENAME).write_text(
            "docs/private/**\n!docs/private/README.md\n",
            encoding="utf-8",
        )

        assert adi.path_matches_autodocignore(repo, "docs/private/secret.md")
        assert not adi.path_matches_autodocignore(repo, "docs/private/README.md")
        assert not adi.path_matches_autodocignore(repo, "docs/public/guide.md")

    def test_returns_false_when_file_missing(self, repo: pathlib.Path) -> None:
        assert not adi.path_matches_autodocignore(repo, "README.md")


class TestBuildAutodocignoreInstructions:
    def test_returns_none_when_file_missing(self, repo: pathlib.Path) -> None:
        assert adi.build_autodocignore_instructions(repo) is None

    def test_includes_active_patterns(self, repo: pathlib.Path) -> None:
        (repo / adi.AUTODOCIGNORE_FILENAME).write_text(
            "helm-charts/**\n",
            encoding="utf-8",
        )
        instructions = adi.build_autodocignore_instructions(repo)
        assert instructions is not None
        assert adi.AUTODOCIGNORE_FILENAME in instructions
        assert "`helm-charts/**`" in instructions
        assert "gitwildmatch" in instructions

    def test_resolve_autodocignore_instructions_only_for_autodoc(
        self, repo: pathlib.Path
    ) -> None:
        (repo / adi.AUTODOCIGNORE_FILENAME).write_text("docs/**\n", encoding="utf-8")
        assert adi.resolve_autodocignore_instructions(repo, "autodoc")
        assert adi.resolve_autodocignore_instructions(repo, "agent-suggestions") == ""


class TestAutodocWorkflowIntegration:
    def test_resolve_agentic_assets_appends_autodocignore(
        self, repo: pathlib.Path
    ) -> None:
        (repo / adi.AUTODOCIGNORE_FILENAME).write_text(
            "legacy/**\n",
            encoding="utf-8",
        )

        resolved = resolver.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="autodoc",
            org_key="obs",
            platform_additional_instructions="platform baseline",
        )

        additional = resolved["additional_instructions"]
        assert "platform baseline" in additional
        assert adi.AUTODOCIGNORE_FILENAME in additional
        assert "`legacy/**`" in additional

    def test_other_workflows_do_not_append_autodocignore(
        self, repo: pathlib.Path
    ) -> None:
        (repo / adi.AUTODOCIGNORE_FILENAME).write_text(
            "legacy/**\n",
            encoding="utf-8",
        )

        resolved = resolver.resolve_agentic_assets(
            repo_root=repo,
            workflow_id="agent-suggestions",
            org_key="obs",
            platform_additional_instructions="platform baseline",
        )

        assert adi.AUTODOCIGNORE_FILENAME not in resolved["additional_instructions"]
