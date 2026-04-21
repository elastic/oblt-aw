"""
Unit tests for scripts/build_target_operations.py

These tests exercise the pure-logic functions (parse_repositories,
parse_bool, write_outputs) in isolation, without touching the network,
the file-system (beyond tmp files created by tmp_path), or git.
"""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

# Make the scripts/ package importable without installation.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "scripts"))

import build_target_operations as bto  # noqa: E402  (after sys.path manipulation)


# ── parse_repositories ────────────────────────────────────────────────────────


class TestParseRepositories:
    def test_list_of_strings(self) -> None:
        content = json.dumps(["elastic/foo", "elastic/bar"])
        result = bto.parse_repositories(content)
        assert result == ["elastic/bar", "elastic/foo"]  # sorted

    def test_object_with_repositories_key(self) -> None:
        content = json.dumps({"repositories": ["elastic/zoo", "elastic/abc"]})
        result = bto.parse_repositories(content)
        assert result == ["elastic/abc", "elastic/zoo"]

    def test_deduplication(self) -> None:
        content = json.dumps(["elastic/dup", "elastic/dup", "elastic/other"])
        result = bto.parse_repositories(content)
        assert result == ["elastic/dup", "elastic/other"]

    def test_whitespace_trimmed(self) -> None:
        content = json.dumps(["  elastic/trimmed  "])
        result = bto.parse_repositories(content)
        assert result == ["elastic/trimmed"]

    def test_empty_repositories_key(self) -> None:
        content = json.dumps({"repositories": []})
        result = bto.parse_repositories(content)
        assert result == []

    def test_empty_list(self) -> None:
        result = bto.parse_repositories(json.dumps([]))
        assert result == []

    def test_empty_string_returns_empty(self) -> None:
        result = bto.parse_repositories("")
        assert result == []

    def test_invalid_entry_raises(self) -> None:
        content = json.dumps(["not-a-valid-repo"])
        with pytest.raises(SystemExit, match="Invalid repository entry"):
            bto.parse_repositories(content)

    def test_non_string_entry_raises(self) -> None:
        content = json.dumps([123])
        with pytest.raises(SystemExit, match="Invalid repository entry"):
            bto.parse_repositories(content)

    def test_invalid_top_level_type_raises(self) -> None:
        content = json.dumps("a string, not a list or dict")
        with pytest.raises(SystemExit):
            bto.parse_repositories(content)

    def test_repositories_not_a_list_raises(self) -> None:
        content = json.dumps({"repositories": "elastic/foo"})
        with pytest.raises(SystemExit, match="`repositories` must be a list"):
            bto.parse_repositories(content)


# ── parse_bool ────────────────────────────────────────────────────────────────


class TestParseBool:
    @pytest.mark.parametrize("value", ["true", "True", "TRUE", "1", "yes", "on"])
    def test_truthy_values(self, value: str) -> None:
        assert bto.parse_bool(value) is True

    @pytest.mark.parametrize("value", ["false", "False", "FALSE", "0", "no", "off", ""])
    def test_falsy_values(self, value: str) -> None:
        assert bto.parse_bool(value) is False

    def test_whitespace_stripped(self) -> None:
        assert bto.parse_bool("  true  ") is True


# ── write_outputs ─────────────────────────────────────────────────────────────


class TestWriteOutputs:
    def test_writes_key_value_pairs(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        output_file = tmp_path / "github_output"
        output_file.touch()
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))

        bto.write_outputs({"targets": "[]", "has_targets": "false"})

        content = output_file.read_text()
        assert "targets=[]\n" in content
        assert "has_targets=false\n" in content

    def test_raises_when_env_not_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("GITHUB_OUTPUT", raising=False)
        with pytest.raises(SystemExit, match="GITHUB_OUTPUT is not set"):
            bto.write_outputs({"key": "value"})


# ── main() integration ────────────────────────────────────────────────────────


class TestMain:
    def _setup_env(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: pathlib.Path,
        *,
        changed_files_count: int = 1,
        force: str = "false",
        base_ref: str = "",
        repos: list[str] | None = None,
    ) -> pathlib.Path:
        output_file = tmp_path / "github_output"
        output_file.touch()
        monkeypatch.setenv("GITHUB_OUTPUT", str(output_file))
        monkeypatch.setenv("CHANGED_FILES_COUNT", str(changed_files_count))
        monkeypatch.setenv("FORCE_DISTRIBUTION", force)
        monkeypatch.setenv("BASE_REF", base_ref)
        monkeypatch.chdir(tmp_path)

        config = {"repositories": repos or ["elastic/foo", "elastic/bar"]}
        (tmp_path / "config").mkdir(exist_ok=True)
        (tmp_path / "config" / "obs").mkdir(exist_ok=True)
        (tmp_path / "config" / "obs" / "workflow-registry.json").write_text(
            json.dumps({"workflows": []})
        )
        (tmp_path / "config" / "obs" / "active-repositories.json").write_text(
            json.dumps(config)
        )
        return output_file

    def test_no_changes_skips_work(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        output_file = self._setup_env(monkeypatch, tmp_path, changed_files_count=0)
        rc = bto.main()
        assert rc == 0
        content = output_file.read_text()
        assert "has_targets=false" in content

    def test_with_changes_builds_targets(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        output_file = self._setup_env(monkeypatch, tmp_path, changed_files_count=2)
        rc = bto.main()
        assert rc == 0
        content = output_file.read_text()
        assert "has_targets=true" in content
        targets = json.loads(
            next(
                line.split("=", 1)[1]
                for line in content.splitlines()
                if line.startswith("targets=")
            )
        )
        repos = {t["repository"] for t in targets}
        assert repos == {"elastic/foo", "elastic/bar"}
        ops = {t["operation"] for t in targets}
        assert ops == {"install"}

    def test_force_distribution(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        output_file = self._setup_env(
            monkeypatch, tmp_path, changed_files_count=0, force="true"
        )
        rc = bto.main()
        assert rc == 0
        content = output_file.read_text()
        assert "has_targets=true" in content

    def test_removed_repositories_added_as_remove_ops(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: pathlib.Path
    ) -> None:
        """When BASE_REF resolves to a previous list with extra repos, those appear as 'remove'."""
        output_file = self._setup_env(
            monkeypatch, tmp_path, changed_files_count=1, repos=["elastic/bar"]
        )

        # Patch read_previous_repositories to simulate a previous state with an extra repo.
        monkeypatch.setattr(
            bto, "read_previous_repositories", lambda _: ["elastic/bar", "elastic/gone"]
        )

        rc = bto.main()
        assert rc == 0
        content = output_file.read_text()
        targets_raw = next(
            line.split("=", 1)[1]
            for line in content.splitlines()
            if line.startswith("targets=")
        )
        targets = json.loads(targets_raw)

        ops_by_repo = {t["repository"]: t["operation"] for t in targets}
        assert ops_by_repo["elastic/bar"] == "install"
        assert ops_by_repo["elastic/gone"] == "remove"
