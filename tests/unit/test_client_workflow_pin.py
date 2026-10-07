"""Unit tests for scripts/client_workflow_pin.py."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import client_workflow_pin as cwp
from common import PIN_CLASS_DEVELOPMENT, PIN_CLASS_PRODUCTION

SAMPLE_YAML = """\
jobs:
  run:
    uses: elastic/oblt-aw/.github/workflows/obs-aw-event-schedule.yml@main # ratchet:exclude
"""


def _pointers(*, sha: str = "", tag: str = "v0") -> dict[str, object]:
    return {
        "schema_version": 1,
        "major": 0,
        "tags": {"current": tag, "next": "next", "previous": "previous"},
        "pointers": {
            "current": {"sha": sha, "semver": "", "updated_at": ""},
            "next": {"sha": "", "semver": "", "updated_at": ""},
            "previous": {"sha": "", "semver": "", "updated_at": ""},
        },
    }


class TestRewriteControlPlaneUsesPin:
    def test_rewrites_main_to_v0(self) -> None:
        updated = cwp.rewrite_control_plane_uses_pin(SAMPLE_YAML, "v0")
        assert "@v0 # ratchet:exclude" in updated
        assert "@main" not in updated

    def test_rewrites_v0_to_main(self) -> None:
        yaml_v0 = SAMPLE_YAML.replace("@main", "@v0")
        updated = cwp.rewrite_control_plane_uses_pin(yaml_v0, "main")
        assert "@main # ratchet:exclude" in updated

    def test_rejects_empty_pin(self) -> None:
        with pytest.raises(SystemExit, match="non-empty"):
            cwp.rewrite_control_plane_uses_pin(SAMPLE_YAML, "  ")


class TestResolveControlPlanePin:
    def test_development_is_always_main(self) -> None:
        sha = "a" * 40
        assert (
            cwp.resolve_control_plane_pin(PIN_CLASS_DEVELOPMENT, _pointers(sha=sha))
            == "main"
        )

    def test_production_stays_main_until_current_sha(self) -> None:
        assert (
            cwp.resolve_control_plane_pin(PIN_CLASS_PRODUCTION, _pointers()) == "main"
        )

    def test_production_uses_tags_current_when_sha_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cwp, "published_moving_tag_exists", lambda tag: True)
        sha = "b" * 40
        assert (
            cwp.resolve_control_plane_pin(
                PIN_CLASS_PRODUCTION, _pointers(sha=sha, tag="v0")
            )
            == "v0"
        )

    def test_production_fails_when_sha_set_and_tag_unpublished(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(cwp, "published_moving_tag_exists", lambda tag: False)
        with pytest.raises(SystemExit, match="not published"):
            cwp.resolve_control_plane_pin(
                PIN_CLASS_PRODUCTION, _pointers(sha="c" * 40, tag="v0")
            )

    def test_unknown_pin_class_fails(self) -> None:
        with pytest.raises(SystemExit, match="Unknown pin-class"):
            cwp.resolve_control_plane_pin("staging", _pointers())


class TestRewriteFilesCli:
    def test_rewrites_listed_yaml(
        self, tmp_path: pathlib.Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        target = tmp_path / "target"
        dest = target / ".github" / "workflows" / "trigger.yml"
        dest.parent.mkdir(parents=True)
        dest.write_text(SAMPLE_YAML, encoding="utf-8")
        monkeypatch.setenv("CONTROL_PLANE_PIN", "v0")
        monkeypatch.setenv("TARGET_ROOT", str(target))
        monkeypatch.setenv(
            "FILES_JSON",
            json.dumps([{"dst": ".github/workflows/trigger.yml"}]),
        )
        assert cwp.main() == 0
        assert "@v0 # ratchet:exclude" in dest.read_text(encoding="utf-8")
