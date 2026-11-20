"""Unit tests for scripts/estc_buildkite_log_tail.py and lock binding."""

from __future__ import annotations

import pathlib
import sys

import pytest
import yaml

_root = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_root / "scripts"))

import estc_buildkite_log_tail as eblt

SOURCE_MD = _root / ".github" / "workflows" / "gh-aw-estc-pr-buildkite-detective.md"
LOCK_YML = (
    _root / ".github" / "workflows" / "gh-aw-estc-pr-buildkite-detective.lock.yml"
)
WRAPPER_YML = _root / ".github" / "workflows" / "obs-aw-estc-pr-buildkite-detective.yml"


class TestParseBuildkiteLogTailLines:
    def test_empty_uses_default(self) -> None:
        assert eblt.parse_buildkite_log_tail_lines(None) == 150
        assert eblt.parse_buildkite_log_tail_lines("") == 150
        assert eblt.parse_buildkite_log_tail_lines("  ") == 150

    @pytest.mark.parametrize("raw,expected", [("1", 1), ("500", 500), ("2000", 2000)])
    def test_accepts_bounds_and_override(self, raw: str, expected: int) -> None:
        assert eblt.parse_buildkite_log_tail_lines(raw) == expected

    @pytest.mark.parametrize("raw", ["0", "-1", "2001", "3.5", "abc", "150x"])
    def test_rejects_invalid(self, raw: str) -> None:
        with pytest.raises(eblt.BuildkiteLogTailError):
            eblt.parse_buildkite_log_tail_lines(raw)


class TestTakeLogTail:
    def test_default_and_override_slice(self) -> None:
        lines = [f"L{i}" for i in range(600)]
        assert eblt.take_log_tail(lines, 150) == lines[-150:]
        assert eblt.take_log_tail(lines, 500) == lines[-500:]
        assert len(eblt.take_log_tail(lines, 150)) == 150
        assert len(eblt.take_log_tail(lines, 500)) == 500

    def test_short_log_returns_all(self) -> None:
        lines = ["a", "b", "c"]
        assert eblt.take_log_tail(lines, 150) == lines

    def test_rejects_non_positive_tail(self) -> None:
        with pytest.raises(eblt.BuildkiteLogTailError):
            eblt.take_log_tail(["x"], 0)


class TestPrefetchBindingContract:
    """Lock/source must bind the input and fail closed before fetch."""

    def test_source_binds_env_and_parses_before_fetch(self) -> None:
        text = SOURCE_MD.read_text(encoding="utf-8")
        assert (
            "BUILDKITE_LOG_TAIL_LINES: ${{ inputs.buildkite-log-tail-lines }}" in text
        )
        assert "LOG_TAIL_DEFAULT = 150" in text
        assert "LOG_TAIL_MAX = 2000" in text
        assert "lines[-LOG_TAIL:]" in text
        parse_at = text.index("raw_tail = os.environ.get('BUILDKITE_LOG_TAIL_LINES'")
        fetch_at = text.index("def bk_get(path):")
        assert parse_at < fetch_at

    def test_lock_binds_env_input(self) -> None:
        text = LOCK_YML.read_text(encoding="utf-8")
        assert (
            "BUILDKITE_LOG_TAIL_LINES: ${{ inputs.buildkite-log-tail-lines }}" in text
        )
        assert "LOG_TAIL_MAX = 2000" in text

    def test_wrapper_null_only_default_preserves_zero(self) -> None:
        data = yaml.safe_load(WRAPPER_YML.read_text(encoding="utf-8"))
        with_block = data["jobs"]["estc-pr-buildkite-detective"]["with"]
        expr = with_block["buildkite-log-tail-lines"]
        assert "== null && 150 ||" in expr
        assert "resolved-inputs-json)['buildkite-log-tail-lines'] || 150" not in expr
