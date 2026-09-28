"""Unit tests for scripts/release_pointers.py."""

from __future__ import annotations

import json
import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import release_pointers as rp


def _minimal_pointers(**overrides: object) -> dict:
    data = {
        "schema_version": 1,
        "major": 1,
        "tags": {
            "prod": "v1",
            "candidate": "candidate",
            "previous_prod": "previous-prod",
        },
        "pointers": {
            "prod": {"sha": "", "semver": "", "updated_at": ""},
            "candidate": {"sha": "", "semver": "", "updated_at": ""},
            "previous_prod": {"sha": "", "semver": "", "updated_at": ""},
        },
    }
    data.update(overrides)
    return data


SHA_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SHA_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"


class TestNormalizeSemver:
    def test_accepts_v_prefix(self) -> None:
        assert rp.normalize_semver("v1.2.3") == "v1.2.3"

    def test_adds_v_prefix(self) -> None:
        assert rp.normalize_semver("1.2.3") == "v1.2.3"

    def test_rejects_garbage(self) -> None:
        with pytest.raises(ValueError):
            rp.normalize_semver("latest")


class TestNextSemver:
    def test_empty_starts_at_v1(self) -> None:
        assert rp.next_semver("", "patch") == "v1.0.0"

    def test_patch(self) -> None:
        assert rp.next_semver("v1.2.3", "patch") == "v1.2.4"

    def test_minor(self) -> None:
        assert rp.next_semver("v1.2.3", "minor") == "v1.3.0"

    def test_major(self) -> None:
        assert rp.next_semver("v1.2.3", "major") == "v2.0.0"

    def test_rejects_unknown_type(self) -> None:
        with pytest.raises(ValueError, match="release_type"):
            rp.next_semver("v1.0.0", "rc")


class TestPlanPromote:
    def test_first_promote_ignores_release_type(self) -> None:
        data = _minimal_pointers()
        plan = rp.plan_promote(data, sha=SHA_A, release_type="major")
        assert plan["semver"] == "v1.0.0"
        assert plan["bootstrap"] is True
        assert plan["previous_sha"] == SHA_A
        assert plan["prod_tag"] == "v1"

    def test_patch_bump(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "prod", sha=SHA_B, semver="v1.0.0")
        plan = rp.plan_promote(data, sha=SHA_A, release_type="patch")
        assert plan["semver"] == "v1.0.1"
        assert plan["bootstrap"] is False
        assert plan["previous_sha"] == SHA_B
        assert plan["previous_semver"] == "v1.0.0"

    def test_major_updates_prod_tag(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "prod", sha=SHA_B, semver="v1.4.2")
        plan = rp.plan_promote(data, sha=SHA_A, release_type="major")
        assert plan["semver"] == "v2.0.0"
        assert plan["prod_tag"] == "v2"

    def test_apply_pointer_updates(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "prod", sha=SHA_B, semver="v1.0.0")
        plan = rp.plan_promote(data, sha=SHA_A, release_type="minor")
        rp.apply_promote_pointer_updates(
            data, plan, updated_at="2026-01-01T00:00:00+00:00"
        )
        assert data["major"] == 1
        assert data["tags"]["prod"] == "v1"
        assert data["pointers"]["prod"]["sha"] == SHA_A
        assert data["pointers"]["prod"]["semver"] == "v1.1.0"
        assert data["pointers"]["previous_prod"]["sha"] == SHA_B
        assert data["pointers"]["previous_prod"]["semver"] == "v1.0.0"


class TestPlanRollback:
    def test_happy_path(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "prod", sha=SHA_A, semver="v1.0.1")
        rp.set_pointer(data, "previous_prod", sha=SHA_B, semver="v1.0.0")
        plan = rp.plan_rollback(data)
        assert plan["rollback_sha"] == SHA_B
        assert plan["displaced_prod_sha"] == SHA_A
        assert plan["prod_tag"] == "v1"

    def test_equal_pointers_fail(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "prod", sha=SHA_A, semver="v1.0.0")
        rp.set_pointer(data, "previous_prod", sha=SHA_A, semver="v1.0.0")
        with pytest.raises(ValueError, match="nothing to rollback"):
            rp.plan_rollback(data)


class TestLoadSaveRoundTrip:
    def test_round_trip(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "release-pointers.json"
        data = _minimal_pointers()
        rp.set_pointer(data, "prod", sha=SHA_A, semver="v1.0.0")
        rp.save_pointers(data, path)
        loaded = rp.load_pointers(path)
        assert loaded["pointers"]["prod"]["sha"] == SHA_A
        assert json.loads(path.read_text(encoding="utf-8"))["major"] == 1
