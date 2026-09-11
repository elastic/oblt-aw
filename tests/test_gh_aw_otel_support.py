from __future__ import annotations

from pathlib import Path

import yaml


def test_buildkite_detective_wrapper_forwards_optional_otel_secret() -> None:
    workflow_path = Path(".github/workflows/obs-aw-estc-pr-buildkite-detective.yml")
    workflow = yaml.load(workflow_path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)

    workflow_call = workflow["on"]["workflow_call"]
    assert workflow_call["secrets"]["GH_AW_DEFAULT_OTLP_HEADERS"]["required"] == "false"

    job_secrets = workflow["jobs"]["estc-pr-buildkite-detective"]["secrets"]
    assert (
        job_secrets["GH_AW_DEFAULT_OTLP_HEADERS"]
        == "${{ secrets.GH_AW_DEFAULT_OTLP_HEADERS }}"
    )
