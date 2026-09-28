"""Unit tests for scripts/release_pointers.py and promote gate helpers."""

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


class TestClassifyRunClass:
    def test_gating_when_sha_matches(self) -> None:
        assert rp.classify_run_class(candidate_ref=SHA_A, github_sha=SHA_A) == "gating"

    def test_smoke_when_empty_candidate(self) -> None:
        assert rp.classify_run_class(candidate_ref="", github_sha=SHA_A) == "smoke"

    def test_smoke_when_mismatch(self) -> None:
        assert rp.classify_run_class(candidate_ref=SHA_A, github_sha=SHA_B) == "smoke"


class TestEnrichSummary:
    def test_eligible_when_gating_pass(self) -> None:
        out = rp.enrich_summary(
            {"pass": True, "skipped": False, "workflow_id": "obs:autodoc"},
            candidate_ref=SHA_A,
            github_sha=SHA_A,
        )
        assert out["run_class"] == "gating"
        assert out["eligible_for_promote"] is True

    def test_ineligible_when_smoke(self) -> None:
        out = rp.enrich_summary(
            {"pass": True, "workflow_id": "obs:autodoc"},
            candidate_ref="",
            github_sha=SHA_A,
        )
        assert out["run_class"] == "smoke"
        assert out["eligible_for_promote"] is False


class TestValidateE2EGate:
    def _ok_summary(self, workflow_id: str) -> dict:
        return rp.enrich_summary(
            {
                "pass": True,
                "skipped": False,
                "workflow_id": workflow_id,
            },
            candidate_ref=SHA_A,
            github_sha=SHA_A,
        )

    def test_all_required_pass(self) -> None:
        summaries = [self._ok_summary(wid) for wid in rp.REQUIRED_E2E_WORKFLOW_IDS]
        rp.validate_e2e_gate_summaries(summaries, expected_candidate_sha=SHA_A)

    def test_missing_workflow_blocks(self) -> None:
        summaries = [self._ok_summary("obs:autodoc")]
        with pytest.raises(ValueError, match="missing E2E summaries"):
            rp.validate_e2e_gate_summaries(summaries, expected_candidate_sha=SHA_A)

    def test_smoke_blocks(self) -> None:
        summaries = [
            rp.enrich_summary(
                {"pass": True, "skipped": False, "workflow_id": wid},
                candidate_ref="",
                github_sha=SHA_A,
            )
            for wid in rp.REQUIRED_E2E_WORKFLOW_IDS
        ]
        with pytest.raises(ValueError, match="E2E gate failed"):
            rp.validate_e2e_gate_summaries(summaries, expected_candidate_sha=SHA_A)


class TestPlanPromote:
    def test_bootstrap_requires_empty_prod(self) -> None:
        data = _minimal_pointers()
        plan = rp.plan_promote(
            data, candidate_sha=SHA_A, semver="v1.0.0", bootstrap=True
        )
        assert plan["previous_sha"] == SHA_A
        assert plan["bootstrap"] is True

    def test_bootstrap_refused_when_prod_set(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "prod", sha=SHA_B, semver="v1.0.0")
        with pytest.raises(ValueError, match="refuse --bootstrap"):
            rp.plan_promote(data, candidate_sha=SHA_A, semver="v1.0.1", bootstrap=True)

    def test_non_bootstrap_requires_prod(self) -> None:
        data = _minimal_pointers()
        with pytest.raises(ValueError, match="use --bootstrap"):
            rp.plan_promote(data, candidate_sha=SHA_A, semver="v1.0.0", bootstrap=False)

    def test_major_mismatch(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "prod", sha=SHA_B, semver="v1.0.0")
        with pytest.raises(ValueError, match="does not match"):
            rp.plan_promote(data, candidate_sha=SHA_A, semver="v2.0.0", bootstrap=False)


class TestPlanRollback:
    def test_happy_path(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "prod", sha=SHA_A, semver="v1.0.1")
        rp.set_pointer(data, "previous_prod", sha=SHA_B, semver="v1.0.0")
        plan = rp.plan_rollback(data)
        assert plan["rollback_sha"] == SHA_B
        assert plan["displaced_prod_sha"] == SHA_A

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
