"""
Unit tests for scripts/build_repos_matrix.py

Tests ``common.parse_repositories``, ``common.write_outputs``, and
``build_repos_matrix.main`` without touching the file-system beyond ``tmp_path``.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

# Make ``scripts/`` (for ``common``) and ``scripts/obs/`` importable without installation.
_root = pathlib.Path(__file__).parent.parent
sys.path.insert(0, str(_root / "scripts"))

import build_repos_matrix as brm  # noqa: E402
from common import parse_repositories  # noqa: E402


# ── parse_repositories (common) ───────────────────────────────────────────────


class TestParseRepositories:
    def test_list_of_strings(self) -> None:
        content = json.dumps(["elastic/foo", "elastic/bar"])
        result = parse_repositories(content)
        assert result == ["elastic/bar", "elastic/foo"]  # sorted

    def test_object_with_repositories_key(self) -> None:
        content = json.dumps({"repositories": ["elastic/zoo", "elastic/abc"]})
        result = parse_repositories(content)
        assert result == ["elastic/abc", "elastic/zoo"]

    def test_deduplication(self) -> None:
        content = json.dumps(["elastic/dup", "elastic/dup", "elastic/other"])
        result = parse_repositories(content)
        assert result == ["elastic/dup", "elastic/other"]

    def test_whitespace_trimmed(self) -> None:
        content = json.dumps(["  elastic/trimmed  "])
        result = parse_repositories(content)
        assert result == ["elastic/trimmed"]

    def test_empty_repositories_key(self) -> None:
        content = json.dumps({"repositories": []})
        result = parse_repositories(content)
        assert result == []

    def test_empty_list(self) -> None:
        result = parse_repositories(json.dumps([]))
        assert result == []

    def test_empty_string_returns_empty(self) -> None:
        result = parse_repositories("")
        assert result == []

    def test_invalid_entry_raises(self) -> None:
        content = json.dumps(["not-a-valid-repo"])
        with pytest.raises(SystemExit, match="Invalid repository entry"):
            parse_repositories(content)

    def test_non_string_entry_raises(self) -> None:
        content = json.dumps([123])
        with pytest.raises(SystemExit, match="Invalid repository entry"):
            parse_repositories(content)

    def test_invalid_top_level_type_raises(self) -> None:
        content = json.dumps("a string, not a list or dict")
        with pytest.raises(SystemExit, match="active-repositories.json must be"):
            parse_repositories(content)

    def test_repositories_not_a_list_raises(self) -> None:
        content = json.dumps({"repositories": "elastic/foo"})
        with pytest.raises(SystemExit, match=r"`repositories` must be a list"):
            parse_repositories(content)


# ── write_outputs ──────────────────────────────────────────────────────────────


class TestWriteOutputs:
    def test_writes_key_value_pairs(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output_file = tmp_path / "github_output"
        output_file.touch()
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        brm.write_outputs({"repos": "[]", "has_repos": "false", "repos_count": "0"})

        content = output_file.read_text()
        assert "repos=[]\n" in content
        assert "has_repos=false\n" in content
        assert "repos_count=0\n" in content

    def test_raises_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        with pytest.raises(SystemExit, match="GITHUB_OUTPUT is not set"):
            brm.write_outputs({"key": "value"})


# ── main() integration ────────────────────────────────────────────────────────


class TestMain:
    def test_no_active_repositories_writes_empty_outputs(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """When no org ``config/<org-key>/`` trees exist, main writes empty outputs."""
        import importlib.util

        output_file = tmp_path / "github_output"
        output_file.touch()
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        # Load script from tmp_path so it resolves repo root to tmp_path
        (tmp_path / "scripts").mkdir(parents=True)
        script_src = pathlib.Path(brm.__file__).read_text()
        (tmp_path / "scripts" / "build_repos_matrix.py").write_text(script_src)
        spec = importlib.util.spec_from_file_location(
            "brm_test",
            tmp_path / "scripts" / "build_repos_matrix.py",
        )
        assert spec and spec.loader
        brm_test = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(brm_test)

        rc = brm_test.main()
        assert rc == 0
        content = output_file.read_text()
        assert "repos=[]" in content
        assert "has_repos=false" in content
        assert "repos_count=0" in content

    def test_with_active_repositories_builds_matrix(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """When an org tree has ``active-repositories.json``, main builds matrix and writes outputs."""
        import importlib.util

        output_file = tmp_path / "github_output"
        output_file.touch()
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        (tmp_path / "scripts").mkdir(parents=True)
        script_src = pathlib.Path(brm.__file__).read_text()
        (tmp_path / "scripts" / "build_repos_matrix.py").write_text(script_src)
        config = {"repositories": ["elastic/foo", "elastic/bar"]}
        (tmp_path / "config").mkdir()
        (tmp_path / "config" / "obs").mkdir()
        (tmp_path / "config" / "obs" / "workflow-registry.json").write_text(
            json.dumps({"workflows": []})
        )
        (tmp_path / "config" / "obs" / "active-repositories.json").write_text(
            json.dumps(config)
        )

        spec = importlib.util.spec_from_file_location(
            "brm_test",
            tmp_path / "scripts" / "build_repos_matrix.py",
        )
        assert spec and spec.loader
        brm_test = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(brm_test)

        rc = brm_test.main()
        assert rc == 0
        content = output_file.read_text()
        assert "has_repos=true" in content
        assert "repos_count=2" in content
        repos_line = next(
            line for line in content.splitlines() if line.startswith("repos=")
        )
        matrix = json.loads(repos_line.split("=", 1)[1])
        assert len(matrix) == 2
        repos = {m["repository"] for m in matrix}
        assert repos == {"elastic/foo", "elastic/bar"}
