"""
Unit tests for scripts/common.py
"""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import common  # noqa: E402


class TestAppendMultilineGithubOutput:
    def test_multiline_value(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output_file = tmp_path / "github_output"
        output_file.touch()
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        common.append_multiline_github_output("MY_VAR", "line1\nline2\nline3")

        content = output_file.read_text()
        lines = content.splitlines()
        # First line: MY_VAR<<DELIMITER
        assert lines[0].startswith("MY_VAR<<")
        delimiter = lines[0][len("MY_VAR<<"):]
        # Middle lines: the value
        assert lines[1] == "line1"
        assert lines[2] == "line2"
        assert lines[3] == "line3"
        # Last line: DELIMITER
        assert lines[4] == delimiter

    def test_value_without_trailing_newline(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output_file = tmp_path / "github_output"
        output_file.touch()
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        common.append_multiline_github_output("KEY", "no-newline")

        content = output_file.read_text()
        lines = content.splitlines()
        assert lines[0].startswith("KEY<<")
        delimiter = lines[0][len("KEY<<"):]
        assert lines[1] == "no-newline"
        assert lines[2] == delimiter

    def test_value_with_trailing_newline(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output_file = tmp_path / "github_output"
        output_file.touch()
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        common.append_multiline_github_output("KEY", "with-newline\n")

        content = output_file.read_text()
        lines = content.splitlines()
        assert lines[0].startswith("KEY<<")
        delimiter = lines[0][len("KEY<<"):]
        assert lines[1] == "with-newline"
        assert lines[2] == delimiter

    def test_empty_value(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output_file = tmp_path / "github_output"
        output_file.touch()
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        common.append_multiline_github_output("EMPTY", "")

        content = output_file.read_text()
        lines = content.splitlines()
        # First line: EMPTY<<DELIMITER
        assert lines[0].startswith("EMPTY<<")
        delimiter = lines[0][len("EMPTY<<"):]
        # Empty value produces a blank line then the closing delimiter
        assert lines[1] == ""
        assert lines[2] == delimiter

    def test_raises_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        with pytest.raises(SystemExit, match="GITHUB_OUTPUT is not set"):
            common.append_multiline_github_output("KEY", "value")

    def test_appends_to_existing_content(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output_file = tmp_path / "github_output"
        output_file.write_text("existing=value\n")
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        common.append_multiline_github_output("NEW_VAR", "new-value")

        content = output_file.read_text()
        assert content.startswith("existing=value\n")
        assert "NEW_VAR<<" in content
        assert "new-value" in content
