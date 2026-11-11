"""Unit tests for shared E2E secret scan helpers (text + artifact trees)."""

from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "obs" / "e2e"))

import e2e_secret_scan as scan

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


class TestCanaryInventory:
    def test_endpoint_is_fixture_config_not_secret(self) -> None:
        assert "E2E_OTLP_CANARY_ENDPOINT" not in scan.env_secret_names()
        assert "E2E_OTLP_CANARY_ENDPOINT" not in scan.REQUIRED_CANARY_ENV_NAMES

    def test_endpoint_absent_from_text_is_not_a_leak(self) -> None:
        # Endpoint URL may remain after redact; requiring it absent would
        # false-fail the gate. Credential canaries still must be absent.
        result = scan.scan_text(
            f"OTEL_EXPORTER_OTLP_ENDPOINT: {CANARY_ENDPOINT}\n",
            env=_full_canary_env(),
        )
        assert result["secret_leak_detected"] is False


class TestScanText:
    def test_detects_canary_headers(self) -> None:
        result = scan.scan_text(
            f"OTEL_EXPORTER_OTLP_HEADERS: {CANARY_HEADERS}\n",
            env=_full_canary_env(),
        )
        assert result["secret_leak_detected"] is True
        assert "env:E2E_OTLP_CANARY_HEADERS" in result["secret_leak_match_ids"]

    def test_detects_basic_password_fragment(self) -> None:
        result = scan.scan_text(
            f"password={CANARY_BASIC_PASSWORD}\n",
            env=_full_canary_env(),
        )
        assert result["secret_leak_detected"] is True
        assert "env:E2E_OTLP_CANARY_BASIC_PASSWORD" in result["secret_leak_match_ids"]

    def test_detects_basic_credential_fragment(self) -> None:
        result = scan.scan_text(
            f"Authorization=Basic {CANARY_BASIC_CREDENTIAL}\n",
            env=_full_canary_env(),
        )
        assert result["secret_leak_detected"] is True
        assert any(
            "E2E_OTLP_CANARY_BASIC" in item for item in result["secret_leak_match_ids"]
        )

    def test_detects_percent_encoded_headers(self) -> None:
        result = scan.scan_text(
            f"raw={CANARY_PERCENT}\n",
            env=_full_canary_env(),
        )
        assert result["secret_leak_detected"] is True
        assert "env:E2E_OTLP_CANARY_PERCENT_HEADERS" in result["secret_leak_match_ids"]

    def test_detects_auth_fragment(self) -> None:
        fragment = (
            "OBLT_AW_E2E_OTLP_CANARY_ID_DO_NOT_USE:"
            "OBLT_AW_E2E_OTLP_CANARY_SECRET_DO_NOT_USE_xx"
        )
        result = scan.scan_text(f"token={fragment}\n", env=_full_canary_env())
        assert result["secret_leak_detected"] is True
        assert any(
            item.endswith(":auth_fragment") for item in result["secret_leak_match_ids"]
        )

    def test_clean_text_passes(self) -> None:
        result = scan.scan_text(
            "OBLT_AW_E2E_SECRET_LEAK_AUDIT_PLANTED\notel_headers=redacted\n",
            env=_full_canary_env(),
        )
        assert result["secret_leak_detected"] is False


class TestScanDirectory:
    def test_scans_yml_tree(self, tmp_path: pathlib.Path) -> None:
        audit = tmp_path / "sandbox" / "firewall" / "audit"
        audit.mkdir(parents=True)
        (audit / "docker-compose.redacted.yml").write_text(
            f"OTEL_EXPORTER_OTLP_HEADERS: {CANARY_HEADERS}\n",
            encoding="utf-8",
        )
        result = scan.scan_directory(tmp_path, env=_full_canary_env())
        assert result["secret_leak_detected"] is True
        assert result["scanned_file_count"] == 1

    def test_marker_helper(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "a.yml"
        path.write_text("OBLT_AW_E2E_SECRET_LEAK_AUDIT_PLANTED\n", encoding="utf-8")
        assert scan.directory_contains_marker(
            tmp_path, "OBLT_AW_E2E_SECRET_LEAK_AUDIT_PLANTED"
        )
        assert not scan.directory_contains_marker(tmp_path, "missing-marker")
