"""Unit tests for dedicated secret-leak agent-artifact E2E harness and oracle."""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import e2e_secret_scan as scan
import oracle_secret_leak_artifacts_e2e as oracle
import secret_leak_artifacts_e2e_harness as harness

TESTDATA_ROOT = ROOT / "testdata" / "agentic" / "secret-leak-artifacts"
LIVE_CASE_ID = "otel-headers-absent-from-agent-artifact-live"

CANARY_HEADERS = (
    "Authorization=ApiKey OBLT_AW_E2E_OTLP_CANARY_ID_DO_NOT_USE:"
    "OBLT_AW_E2E_OTLP_CANARY_SECRET_DO_NOT_USE_xx"
)
CANARY_ENDPOINT = "https://e2e-otlp-canary.invalid.example.oblt-aw:443"
CANARY_BASIC_PASSWORD = "OBLT_AW_E2E_OTLP_BASIC_PASSWORD_DO_NOT_USE_xx"
CANARY_BASIC_DECODED = f"e2e-otlp-canary-user:{CANARY_BASIC_PASSWORD}"
CANARY_BASIC_CREDENTIAL = "ZTJlLW90bHAtY2FuYXJ5LXVzZXI6T0JMVF9BV19FMkVfT1RMUF9CQVNJQ19QQVNTV09SRF9ET19OT1RfVVNFX3h4"
CANARY_BASIC_HEADERS = f"Authorization=Basic {CANARY_BASIC_CREDENTIAL}"
CANARY_PERCENT = (
    "Authorization=ApiKey%20OBLT_AW_E2E_OTLP_CANARY_ID_DO_NOT_USE"
    "%3AOBLT_AW_E2E_OTLP_CANARY_SECRET_DO_NOT_USE_xx"
)
CANARY_ALL = f"{CANARY_HEADERS},{CANARY_BASIC_HEADERS}"
MARKER = "OBLT_AW_E2E_SECRET_LEAK_AUDIT_PLANTED"


def _full_canary_env() -> dict[str, str]:
    return {
        "E2E_OTLP_CANARY_ALL_HEADERS": CANARY_ALL,
        "E2E_OTLP_CANARY_BASIC_CREDENTIAL": CANARY_BASIC_CREDENTIAL,
        "E2E_OTLP_CANARY_BASIC_DECODED": CANARY_BASIC_DECODED,
        "E2E_OTLP_CANARY_BASIC_HEADERS": CANARY_BASIC_HEADERS,
        "E2E_OTLP_CANARY_BASIC_PASSWORD": CANARY_BASIC_PASSWORD,
        "E2E_OTLP_CANARY_ENDPOINT": CANARY_ENDPOINT,
        "E2E_OTLP_CANARY_HEADERS": CANARY_HEADERS,
        "E2E_OTLP_CANARY_PERCENT_HEADERS": CANARY_PERCENT,
    }


def _set_canaries(monkeypatch) -> None:
    for name, value in _full_canary_env().items():
        monkeypatch.setenv(name, value)


def _synthetic_live_outcome(*, blocked: bool = False) -> dict:
    outcome = {
        "workflow_id": "obs:secret-leak-artifacts",
        "case_id": LIVE_CASE_ID,
        "layer": "e2e",
        "mode": "live",
        "blocked": blocked,
        "artifact_downloaded": True,
        "audit_marker_verified": True,
        "audit_marker_detail": "ok",
        "gitleaks_clean": True,
        "gitleaks_detail": "gitleaks reported no findings",
        "secret_leak_detected": False,
        "secret_leak_detail": "no secret leak patterns or known env secret values detected",
        "fixture": {
            "artifact_name": "e2e-secret-leak-agent",
            "comparable_secret_env_names": list(scan.REQUIRED_CANARY_ENV_NAMES),
        },
    }
    if blocked:
        outcome["block_reason"] = "blocked for test"
        outcome["audit_marker_verified"] = False
        outcome["gitleaks_clean"] = None
        outcome["secret_leak_detected"] = None
    return outcome


def _fake_gitleaks_clean(*_args, **_kwargs) -> dict:
    return {
        "gitleaks_clean": True,
        "gitleaks_finding_count": 0,
        "gitleaks_detail": "gitleaks reported no findings",
        "gitleaks_rule_ids": [],
    }


def _evaluate(outcome: dict) -> dict:
    case_id = str(outcome.get("case_id") or "")
    expectations = oracle.load_case_expectations(TESTDATA_ROOT, case_id)
    return oracle.evaluate_outcome(outcome, case_expectations=expectations)


class TestGitleaksFields:
    def test_empty_report_is_clean(self) -> None:
        fields = scan.gitleaks_fields_from_report([])
        assert fields["gitleaks_clean"] is True
        assert fields["gitleaks_finding_count"] == 0
        assert fields["gitleaks_rule_ids"] == []

    def test_findings_list_rule_ids_only(self) -> None:
        fields = scan.gitleaks_fields_from_report(
            [
                {"RuleID": "otlp-authorization-apikey", "Secret": "should-not-echo"},
                {"RuleID": "otlp-authorization-basic"},
                {"RuleID": "otlp-authorization-apikey"},
            ]
        )
        assert fields["gitleaks_clean"] is False
        assert fields["gitleaks_rule_ids"] == [
            "otlp-authorization-apikey",
            "otlp-authorization-basic",
        ]
        assert "should-not-echo" not in fields["gitleaks_detail"]


class TestOracle:
    def test_happy_path_passes(self) -> None:
        report = _evaluate(_synthetic_live_outcome())
        assert report["pass"] is True
        check_ids = {c["id"] for c in report["checks"]}
        assert "secret_leak_absent" in check_ids
        assert "gitleaks_clean" in check_ids
        assert "audit_marker_verified" in check_ids
        assert "artifact_downloaded" in check_ids
        assert "require_canary_env" in check_ids

    def test_rejects_gitleaks_not_clean(self) -> None:
        outcome = _synthetic_live_outcome()
        outcome["gitleaks_clean"] = False
        outcome["gitleaks_detail"] = (
            "gitleaks finding rule id(s): otlp-authorization-apikey"
        )
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert any(
            c["id"] == "gitleaks_clean" and not c["pass"] for c in report["checks"]
        )

    def test_rejects_missing_gitleaks_field(self) -> None:
        outcome = _synthetic_live_outcome()
        del outcome["gitleaks_clean"]
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert any(
            c["id"] == "gitleaks_clean" and not c["pass"] for c in report["checks"]
        )

    def test_blocked_fails(self) -> None:
        report = _evaluate(_synthetic_live_outcome(blocked=True))
        assert report["pass"] is False
        assert any(c["id"] == "not_blocked" and not c["pass"] for c in report["checks"])

    def test_rejects_missing_leak_field(self) -> None:
        outcome = _synthetic_live_outcome()
        del outcome["secret_leak_detected"]
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert any(
            c["id"] == "secret_leak_absent" and not c["pass"] for c in report["checks"]
        )

    def test_rejects_leak_detected_true(self) -> None:
        outcome = _synthetic_live_outcome()
        outcome["secret_leak_detected"] = True
        outcome["secret_leak_detail"] = (
            "secret leak match(es): env:E2E_OTLP_CANARY_BASIC_PASSWORD"
        )
        report = _evaluate(outcome)
        assert report["pass"] is False

    def test_rejects_partial_canary_env(self) -> None:
        outcome = _synthetic_live_outcome()
        outcome["fixture"]["comparable_secret_env_names"] = [
            "E2E_OTLP_CANARY_ENDPOINT",
            "E2E_OTLP_CANARY_HEADERS",
        ]
        report = _evaluate(outcome)
        assert report["pass"] is False
        assert any(
            c["id"] == "require_canary_env" and not c["pass"] for c in report["checks"]
        )

    def test_rejects_missing_case_expectations(self) -> None:
        report = oracle.evaluate_outcome(
            _synthetic_live_outcome(), case_expectations=None
        )
        assert report["pass"] is False
        assert any(
            c["id"] == "case_expectations" and not c["pass"] for c in report["checks"]
        )

    def test_schema_rejects_partial_expectations(self) -> None:
        err = oracle.case_expectations_schema_error("live", {"typo": True})
        assert err is not None
        assert "missing required live expectation keys" in err


class TestHarness:
    def test_live_case_clean_artifact(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:
        _set_canaries(monkeypatch)
        monkeypatch.setattr(harness, "run_gitleaks_dir", _fake_gitleaks_clean)
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        (artifact / "docker-compose.redacted.yml").write_text(
            f"# {MARKER}\nservices: {{}}\n",
            encoding="utf-8",
        )
        case_dir = TESTDATA_ROOT / "cases" / LIVE_CASE_ID
        outcome = harness.run_live_case(
            case_dir,
            artifact_dir=artifact,
            gitleaks_bin="gitleaks",
            gitleaks_config=TESTDATA_ROOT / "gitleaks.toml",
        )
        assert outcome["blocked"] is False
        assert outcome["secret_leak_detected"] is False
        assert outcome["gitleaks_clean"] is True
        assert outcome["audit_marker_verified"] is True
        assert outcome["artifact_downloaded"] is True

    def test_live_case_requires_gitleaks_bin(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:
        _set_canaries(monkeypatch)
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        (artifact / "docker-compose.redacted.yml").write_text(
            f"# {MARKER}\nservices: {{}}\n",
            encoding="utf-8",
        )
        case_dir = TESTDATA_ROOT / "cases" / LIVE_CASE_ID
        outcome = harness.run_live_case(case_dir, artifact_dir=artifact)
        assert outcome["blocked"] is True
        assert outcome["gitleaks_clean"] is False
        assert "gitleaks-bin" in str(outcome.get("block_reason") or "")

    def test_live_case_gitleaks_findings_block(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:
        _set_canaries(monkeypatch)

        def _dirty(*_args, **_kwargs) -> dict:
            return {
                "gitleaks_clean": False,
                "gitleaks_finding_count": 1,
                "gitleaks_detail": (
                    "gitleaks finding rule id(s): otlp-authorization-apikey"
                ),
                "gitleaks_rule_ids": ["otlp-authorization-apikey"],
            }

        monkeypatch.setattr(harness, "run_gitleaks_dir", _dirty)
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        (artifact / "docker-compose.redacted.yml").write_text(
            f"# {MARKER}\nservices: {{}}\n",
            encoding="utf-8",
        )
        case_dir = TESTDATA_ROOT / "cases" / LIVE_CASE_ID
        outcome = harness.run_live_case(
            case_dir,
            artifact_dir=artifact,
            gitleaks_bin="gitleaks",
            gitleaks_config=TESTDATA_ROOT / "gitleaks.toml",
        )
        assert outcome["blocked"] is True
        assert outcome["gitleaks_clean"] is False
        assert "gitleaks" in str(outcome.get("block_reason") or "").lower()

    def test_live_case_detects_basic_password(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:
        _set_canaries(monkeypatch)
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        (artifact / "otlp-credential-variants.json").write_text(
            f'# {MARKER}\n{{"basic_password": "{CANARY_BASIC_PASSWORD}"}}\n',
            encoding="utf-8",
        )
        case_dir = TESTDATA_ROOT / "cases" / LIVE_CASE_ID
        outcome = harness.run_live_case(case_dir, artifact_dir=artifact)
        assert outcome["blocked"] is True
        assert outcome["secret_leak_detected"] is True
        assert "secret leak" in str(outcome.get("block_reason") or "").lower()

    def test_live_case_detects_canary(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:
        _set_canaries(monkeypatch)
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        (artifact / "docker-compose.redacted.yml").write_text(
            f"# {MARKER}\nOTEL_EXPORTER_OTLP_HEADERS: {CANARY_HEADERS}\n",
            encoding="utf-8",
        )
        case_dir = TESTDATA_ROOT / "cases" / LIVE_CASE_ID
        outcome = harness.run_live_case(case_dir, artifact_dir=artifact)
        assert outcome["blocked"] is True
        assert outcome["secret_leak_detected"] is True

    def test_live_case_missing_marker(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:
        _set_canaries(monkeypatch)
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        (artifact / "docker-compose.redacted.yml").write_text(
            "services: {}\n",
            encoding="utf-8",
        )
        case_dir = TESTDATA_ROOT / "cases" / LIVE_CASE_ID
        outcome = harness.run_live_case(case_dir, artifact_dir=artifact)
        assert outcome["blocked"] is True
        assert outcome["audit_marker_verified"] is False

    def test_live_case_missing_canary_env(
        self, tmp_path: pathlib.Path, monkeypatch
    ) -> None:
        for name in scan.REQUIRED_CANARY_ENV_NAMES:
            monkeypatch.delenv(name, raising=False)
        artifact = tmp_path / "artifact"
        artifact.mkdir()
        (artifact / "a.yml").write_text(f"{MARKER}\n", encoding="utf-8")
        case_dir = TESTDATA_ROOT / "cases" / LIVE_CASE_ID
        outcome = harness.run_live_case(case_dir, artifact_dir=artifact)
        assert outcome["blocked"] is True
        assert "E2E_OTLP_CANARY" in str(outcome.get("block_reason") or "")

    def test_case_json_round_trip(self) -> None:
        case_path = TESTDATA_ROOT / "cases" / LIVE_CASE_ID / "case.json"
        case = json.loads(case_path.read_text(encoding="utf-8"))
        assert case["id"] == LIVE_CASE_ID
        assert case["mode"] == "live"
        expectations = oracle.load_case_expectations(TESTDATA_ROOT, LIVE_CASE_ID)
        assert oracle.case_expectations_schema_error("live", expectations) is None
