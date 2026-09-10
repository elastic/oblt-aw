from __future__ import annotations

from pathlib import Path


def test_buildkite_detective_declares_otel_secret() -> None:
    workflow_path = Path(".github/workflows/gh-aw-estc-pr-buildkite-detective.md")
    text = workflow_path.read_text(encoding="utf-8")

    assert "GH_AW_DEFAULT_OTLP_HEADERS" in text
    assert "required: false" in text
