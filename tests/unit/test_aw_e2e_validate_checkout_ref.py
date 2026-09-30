"""Unit tests for scripts/aw_e2e_validate_checkout_ref.py."""

from __future__ import annotations

import pathlib
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))

import aw_e2e_validate_checkout_ref as guard


class TestValidateDispatchCheckoutRef:
    def test_accepts_default_branch_name(self) -> None:
        guard.validate_dispatch_checkout_ref(
            checkout_ref="main",
            default_branch="main",
            github_ref="refs/heads/main",
        )

    def test_rejects_dispatch_from_feature_branch(self) -> None:
        with pytest.raises(ValueError, match="must run from refs/heads/main"):
            guard.validate_dispatch_checkout_ref(
                checkout_ref="main",
                default_branch="main",
                github_ref="refs/heads/evil",
            )

    def test_rejects_non_sha_feature_ref(self) -> None:
        with pytest.raises(ValueError, match="40-char SHA"):
            guard.validate_dispatch_checkout_ref(
                checkout_ref="feature/evil",
                default_branch="main",
                github_ref="refs/heads/main",
            )

    def test_rejects_sha_not_on_default_history(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        sha = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

        def fake_run_git(args: list[str]) -> object:
            class Result:
                returncode = 0
                stdout = ""
                stderr = ""

            if args[:2] == ["merge-base", "--is-ancestor"]:
                result = Result()
                result.returncode = 1
                return result
            return Result()

        monkeypatch.setattr(guard, "_run_git", fake_run_git)
        with pytest.raises(ValueError, match="not an ancestor"):
            guard.validate_dispatch_checkout_ref(
                checkout_ref=sha,
                default_branch="main",
                github_ref="refs/heads/main",
            )
