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
        "major": 0,
        "tags": {
            "current": "v0",
            "next": "next",
            "previous": "previous",
        },
        "pointers": {
            "current": {"sha": "", "semver": "", "updated_at": ""},
            "next": {"sha": "", "semver": "", "updated_at": ""},
            "previous": {"sha": "", "semver": "", "updated_at": ""},
        },
    }
    data.update(overrides)
    return data


SHA_A = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
SHA_B = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
SHA_C = "cccccccccccccccccccccccccccccccccccccccc"


class TestNormalizeSemver:
    def test_accepts_v_prefix(self) -> None:
        assert rp.normalize_semver("v1.2.3") == "v1.2.3"

    def test_adds_v_prefix(self) -> None:
        assert rp.normalize_semver("1.2.3") == "v1.2.3"

    def test_rejects_garbage(self) -> None:
        with pytest.raises(ValueError):
            rp.normalize_semver("latest")


class TestBootstrapSemver:
    def test_uses_configured_major(self) -> None:
        assert rp.bootstrap_semver(_minimal_pointers()) == "v0.0.0"

    def test_honors_override_major(self) -> None:
        assert rp.bootstrap_semver(_minimal_pointers(major=1)) == "v1.0.0"

    def test_rejects_negative_major(self) -> None:
        with pytest.raises(ValueError, match="major"):
            rp.bootstrap_semver(_minimal_pointers(major=-1))


class TestNextSemver:
    def test_empty_requires_bootstrap(self) -> None:
        with pytest.raises(ValueError, match="bootstrap_semver"):
            rp.next_semver("", "patch")

    def test_patch(self) -> None:
        assert rp.next_semver("v0.2.3", "patch") == "v0.2.4"

    def test_minor(self) -> None:
        assert rp.next_semver("v0.2.3", "minor") == "v0.3.0"

    def test_major_graduates_to_v1(self) -> None:
        assert rp.next_semver("v0.2.3", "major") == "v1.0.0"

    def test_rejects_unknown_type(self) -> None:
        with pytest.raises(ValueError, match="release_type"):
            rp.next_semver("v0.0.0", "rc")


class TestHighestPointerSemver:
    def test_uses_max_across_pointers(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "current", sha=SHA_A, semver="v0.0.0")
        rp.set_pointer(data, "previous", sha=SHA_B, semver="v0.0.1")
        assert rp.highest_pointer_semver(data) == "v0.0.1"


class TestPlanPromote:
    def test_first_promote_ignores_release_type(self) -> None:
        data = _minimal_pointers()
        plan = rp.plan_promote(data, sha=SHA_A, release_type="major")
        assert plan["semver"] == "v0.0.0"
        assert plan["bootstrap"] is True
        assert plan["previous_sha"] == SHA_A
        assert plan["current_tag"] == "v0"

    def test_bootstrap_rejects_partial_pointer_state(self) -> None:
        data = _minimal_pointers()
        data["pointers"]["current"] = {
            "sha": "",
            "semver": "v0.0.0",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        with pytest.raises(ValueError, match="partial pointer state"):
            rp.plan_promote(data, sha=SHA_A, release_type="patch")

    def test_bootstrap_rejects_sibling_pointer_residue(self) -> None:
        data = _minimal_pointers()
        data["pointers"]["next"] = {
            "sha": SHA_B,
            "semver": "",
            "updated_at": "",
        }
        with pytest.raises(ValueError, match="partial pointer state"):
            rp.plan_promote(data, sha=SHA_A, release_type="patch")

    def test_bootstrap_rejects_non_string_pointer_fields(self) -> None:
        data = _minimal_pointers()
        data["pointers"]["current"] = {
            "sha": 0,
            "semver": "",
            "updated_at": "",
        }
        with pytest.raises(TypeError, match="pointers.current.sha must be a string"):
            rp.plan_promote(data, sha=SHA_A, release_type="patch")

    def test_bootstrap_rejects_null_semver(self) -> None:
        data = _minimal_pointers()
        data["pointers"]["previous"] = {
            "sha": "",
            "semver": None,
            "updated_at": "",
        }
        with pytest.raises(
            TypeError, match="pointers.previous.semver must be a string"
        ):
            rp.plan_promote(data, sha=SHA_A, release_type="patch")

    def test_rejects_semver_shaped_next_tag(self) -> None:
        data = _minimal_pointers()
        data["tags"]["next"] = "v0.0.99"
        with pytest.raises(ValueError, match="semver-shaped"):
            rp.plan_promote(data, sha=SHA_A, release_type="patch")

    def test_patch_bump(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "current", sha=SHA_B, semver="v0.0.0")
        plan = rp.plan_promote(data, sha=SHA_A, release_type="patch")
        assert plan["semver"] == "v0.0.1"
        assert plan["bootstrap"] is False
        assert plan["previous_sha"] == SHA_B
        assert plan["previous_semver"] == "v0.0.0"

    def test_major_updates_current_tag(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "current", sha=SHA_B, semver="v0.4.2")
        plan = rp.plan_promote(data, sha=SHA_A, release_type="major")
        assert plan["semver"] == "v1.0.0"
        assert plan["current_tag"] == "v1"

    def test_promote_after_rollback_stays_monotonic(self) -> None:
        data = _minimal_pointers()
        # After rolling back v0.0.1 → v0.0.0, previous keeps the displaced release.
        rp.set_pointer(data, "current", sha=SHA_B, semver="v0.0.0")
        rp.set_pointer(data, "previous", sha=SHA_A, semver="v0.0.1")
        plan = rp.plan_promote(data, sha=SHA_A, release_type="patch")
        assert plan["semver"] == "v0.0.2"

    def test_apply_pointer_updates(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "current", sha=SHA_B, semver="v0.0.0")
        plan = rp.plan_promote(data, sha=SHA_A, release_type="minor")
        rp.apply_promote_pointer_updates(
            data, plan, updated_at="2026-01-01T00:00:00+00:00"
        )
        assert data["major"] == 0
        assert data["tags"]["current"] == "v0"
        assert data["pointers"]["current"]["sha"] == SHA_A
        assert data["pointers"]["current"]["semver"] == "v0.1.0"
        assert data["pointers"]["previous"]["sha"] == SHA_B
        assert data["pointers"]["previous"]["semver"] == "v0.0.0"


class TestPlanRollback:
    def test_happy_path(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "current", sha=SHA_A, semver="v0.0.1")
        rp.set_pointer(data, "previous", sha=SHA_B, semver="v0.0.0")
        plan = rp.plan_rollback(data)
        assert plan["rollback_sha"] == SHA_B
        assert plan["displaced_current_sha"] == SHA_A
        assert plan["current_tag"] == "v0"

    def test_retargets_current_major_after_major_promote(self) -> None:
        data = _minimal_pointers()
        data["tags"]["current"] = "v1"
        data["major"] = 1
        rp.set_pointer(data, "current", sha=SHA_A, semver="v1.0.0")
        rp.set_pointer(data, "previous", sha=SHA_B, semver="v0.4.2")
        plan = rp.plan_rollback(data)
        assert plan["current_tag"] == "v1"
        assert plan["rollback_semver"] == "v0.4.2"
        assert plan["displaced_current_semver"] == "v1.0.0"

    def test_rejects_empty_current_semver(self) -> None:
        data = _minimal_pointers()
        data["pointers"]["current"] = {
            "sha": SHA_A,
            "semver": "",
            "updated_at": "2026-01-01T00:00:00+00:00",
        }
        rp.set_pointer(data, "previous", sha=SHA_B, semver="v0.0.0")
        with pytest.raises(ValueError, match="current.semver is empty"):
            rp.plan_rollback(data)

    def test_equal_pointers_fail(self) -> None:
        data = _minimal_pointers()
        rp.set_pointer(data, "current", sha=SHA_A, semver="v0.0.0")
        rp.set_pointer(data, "previous", sha=SHA_A, semver="v0.0.0")
        with pytest.raises(ValueError, match="nothing to rollback"):
            rp.plan_rollback(data)

    def test_apply_rollback_pointer_updates(self) -> None:
        data = _minimal_pointers()
        data["tags"]["current"] = "v1"
        data["major"] = 1
        rp.set_pointer(data, "current", sha=SHA_A, semver="v1.0.0")
        rp.set_pointer(data, "previous", sha=SHA_B, semver="v0.4.2")
        plan = rp.plan_rollback(data)
        rp.apply_rollback_pointer_updates(
            data, plan, updated_at="2026-01-01T00:00:00+00:00"
        )
        assert data["tags"]["current"] == "v1"
        assert data["major"] == 1
        assert data["pointers"]["current"]["sha"] == SHA_B
        assert data["pointers"]["current"]["semver"] == "v0.4.2"
        assert data["pointers"]["previous"]["sha"] == SHA_A
        assert data["pointers"]["previous"]["semver"] == "v1.0.0"


def _git_result(stdout: str = "", returncode: int = 0) -> object:
    return type("R", (), {"returncode": returncode, "stdout": stdout, "stderr": ""})()


class TestRemoteTagCommitSha:
    def test_prefers_peeled_commit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check
            assert args == [
                "ls-remote",
                "origin",
                "refs/tags/v0.0.0",
                "refs/tags/v0.0.0^{}",
            ]
            return _git_result(
                f"{SHA_B}\trefs/tags/v0.0.0\n{SHA_A}\trefs/tags/v0.0.0^{{}}\n"
            )

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        assert rp.remote_tag_commit_sha("v0.0.0") == SHA_A

    def test_uses_direct_sha_for_lightweight_tag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check
            assert args[-2:] == ["refs/tags/v0.0.0", "refs/tags/v0.0.0^{}"]
            return _git_result(f"{SHA_A}\trefs/tags/v0.0.0\n")

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        assert rp.remote_tag_commit_sha("v0.0.0") == SHA_A

    def test_missing_tag_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(rp, "run_git", lambda *a, **k: _git_result("", 0))
        assert rp.remote_tag_commit_sha("v0.0.0") is None


class TestRequireRemoteCurrentAllowsInFlight:
    def _with_current(self) -> dict:
        data = _minimal_pointers()
        rp.set_pointer(data, "current", sha=SHA_A, semver="v0.0.0")
        return data

    def test_skips_when_pointers_current_empty(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rp, "remote_tag_commit_sha", lambda *a, **k: SHA_B)
        rp.require_remote_current_allows_in_flight(
            _minimal_pointers(), in_flight_sha=SHA_A
        )

    def test_allows_when_remote_matches_pointers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rp, "remote_tag_commit_sha", lambda *a, **k: SHA_A)
        rp.require_remote_current_allows_in_flight(
            self._with_current(), in_flight_sha=SHA_B
        )

    def test_allows_retry_when_remote_already_at_in_flight_sha(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rp, "remote_tag_commit_sha", lambda *a, **k: SHA_B)
        rp.require_remote_current_allows_in_flight(
            self._with_current(), in_flight_sha=SHA_B
        )

    def test_refuses_when_remote_matches_neither(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rp, "remote_tag_commit_sha", lambda *a, **k: SHA_B)
        with pytest.raises(ValueError, match="refuse until they agree"):
            rp.require_remote_current_allows_in_flight(
                self._with_current(), in_flight_sha=SHA_C
            )

    def test_refuses_when_pointer_set_but_tag_missing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(rp, "remote_tag_commit_sha", lambda *a, **k: None)
        with pytest.raises(ValueError, match="is not on origin"):
            rp.require_remote_current_allows_in_flight(
                self._with_current(), in_flight_sha=SHA_B
            )


class TestMoveTag:
    def test_creates_lightweight_force_tag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check
            calls.append(args)
            return _git_result("")

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        rp.move_tag("v0", SHA_A, message="current v0.0.0")
        assert calls == [["tag", "-f", "v0", SHA_A]]


class TestCreateImmutableSemverTag:
    def test_creates_when_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[list[str]] = []

        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check
            calls.append(args)
            if args[:2] == ["tag", "-l"]:
                return _git_result("")
            if args[0] == "ls-remote":
                return _git_result("")
            return _git_result("")

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        assert (
            rp.create_immutable_semver_tag("v0.0.0", SHA_A, message="oblt-aw") is True
        )
        assert ["tag", "v0.0.0", SHA_A] in calls
        assert not any("-a" in args for args in calls)

    def test_skips_when_local_tag_points_at_planned_sha(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check
            calls.append(args)
            if args[:2] == ["tag", "-l"]:
                return _git_result("v0.0.0\n")
            if args[0] == "rev-parse":
                return _git_result(f"{SHA_A}\n")
            raise AssertionError(args)

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        assert (
            rp.create_immutable_semver_tag("v0.0.0", SHA_A, message="oblt-aw") is False
        )
        assert not any(args[:2] == ["tag", "v0.0.0"] for args in calls)
        assert not any("-a" in args for args in calls)

    def test_fails_when_local_tag_points_elsewhere(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check
            if args[:2] == ["tag", "-l"]:
                return _git_result("v0.0.0\n")
            if args[0] == "rev-parse":
                return _git_result(f"{SHA_B}\n")
            raise AssertionError(args)

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        with pytest.raises(ValueError, match="already exists at"):
            rp.create_immutable_semver_tag("v0.0.0", SHA_A, message="oblt-aw")

    def test_fetches_when_origin_tag_points_at_planned_sha(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check
            calls.append(args)
            if args[:2] == ["tag", "-l"]:
                return _git_result("")
            if args[0] == "ls-remote":
                return _git_result(f"{SHA_A}\trefs/tags/v0.0.0\n")
            if args[0] == "fetch":
                return _git_result("")
            raise AssertionError(args)

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        assert (
            rp.create_immutable_semver_tag("v0.0.0", SHA_A, message="oblt-aw") is False
        )
        assert [
            "fetch",
            "origin",
            "refs/tags/v0.0.0:refs/tags/v0.0.0",
        ] in calls
        assert not any(args[:2] == ["tag", "v0.0.0"] for args in calls)
        assert not any("-a" in args for args in calls)

    def test_fails_when_origin_tag_points_elsewhere(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check
            if args[:2] == ["tag", "-l"]:
                return _git_result("")
            if args[0] == "ls-remote":
                return _git_result(f"{SHA_B}\trefs/tags/v0.0.0\n")
            raise AssertionError(args)

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        with pytest.raises(ValueError, match="already exists on origin"):
            rp.create_immutable_semver_tag("v0.0.0", SHA_A, message="oblt-aw")


class TestPushTagHelpers:
    def test_push_promote_tags_splits_force(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            calls.append(args)
            if args[0] == "rev-parse":
                return _git_result(f"{SHA_A}\n")
            if args[0] == "ls-remote":
                return _git_result("")
            return _git_result("")

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        plan = {
            "semver": "v0.0.1",
            "current_tag": "v0",
            "next_tag": "next",
            "previous_tag": "previous",
        }
        rp.push_promote_tags(plan)
        immutable = ["push", "origin", "v0.0.1"]
        assert immutable in calls
        assert "--force" not in immutable
        moving = [c for c in calls if c[:2] == ["push", "origin"] and "--force" in c]
        assert moving
        assert "v0.0.1" not in moving[0]

    def test_push_promote_tags_normalizes_unprefixed_semver(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            calls.append(args)
            if args[0] == "rev-parse":
                return _git_result(f"{SHA_A}\n")
            if args[0] == "ls-remote":
                return _git_result("")
            return _git_result("")

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        plan = {
            "semver": "0.0.1",
            "current_tag": "v0",
            "next_tag": "next",
            "previous_tag": "previous",
        }
        rp.push_promote_tags(plan)
        assert ["push", "origin", "v0.0.1"] in calls

    def test_skips_immutable_push_when_origin_already_at_local_sha(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls: list[list[str]] = []

        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            calls.append(args)
            if args[0] == "rev-parse":
                return _git_result(f"{SHA_A}\n")
            if args[0] == "ls-remote":
                return _git_result(f"{SHA_A}\trefs/tags/v0.0.1\n")
            return _git_result("")

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        rp.push_immutable_tags(["v0.0.1"])
        assert not any(args[:2] == ["push", "origin"] for args in calls)

    def test_fails_immutable_push_when_origin_sha_differs(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            if args[0] == "rev-parse":
                return _git_result(f"{SHA_A}\n")
            if args[0] == "ls-remote":
                return _git_result(f"{SHA_B}\trefs/tags/v0.0.1\n")
            raise AssertionError(args)

        monkeypatch.setattr(rp, "run_git", fake_run_git)
        with pytest.raises(ValueError, match="already exists on origin"):
            rp.push_immutable_tags(["v0.0.1"])


class TestRequireAncestorOf:
    def test_accepts_when_sha_is_tip(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_resolve(ref: str) -> str:
            if ref == "origin/main":
                return SHA_A
            raise AssertionError(ref)

        monkeypatch.setattr(rp, "resolve_sha", fake_resolve)
        rp.require_ancestor_of(SHA_A, tip_ref="origin/main")

    def test_accepts_when_sha_is_ancestor(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def fake_resolve(ref: str) -> str:
            if ref == "origin/main":
                return SHA_B
            raise AssertionError(ref)

        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check
            assert args[:3] == ["merge-base", "--is-ancestor", SHA_A]
            return type("R", (), {"returncode": 0})()

        monkeypatch.setattr(rp, "resolve_sha", fake_resolve)
        monkeypatch.setattr(rp, "run_git", fake_run_git)
        rp.require_ancestor_of(SHA_A, tip_ref="origin/main")

    def test_rejects_when_not_ancestor(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def fake_resolve(ref: str) -> str:
            if ref == "origin/main":
                return SHA_B
            raise AssertionError(ref)

        def fake_run_git(args: list[str], *, check: bool = True) -> object:
            del check, args
            return type("R", (), {"returncode": 1})()

        monkeypatch.setattr(rp, "resolve_sha", fake_resolve)
        monkeypatch.setattr(rp, "run_git", fake_run_git)
        with pytest.raises(ValueError, match="not an ancestor"):
            rp.require_ancestor_of(SHA_A, tip_ref="origin/main")


class TestCreateGithubRelease:
    def test_bootstrap_omits_notes_start_tag(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[list[str]] = []

        def fake_run(
            cmd: list[str],
            *,
            check: bool = False,
            capture_output: bool = False,
            text: bool = False,
        ) -> object:
            del check, capture_output, text
            seen.append(cmd)
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

        monkeypatch.setattr(rp.subprocess, "run", fake_run)
        rp.create_github_release(
            semver="v0.0.0",
            sha=SHA_A,
            previous_semver="v0.0.0",
            bootstrap=True,
        )
        assert seen == [
            [
                "gh",
                "release",
                "create",
                "v0.0.0",
                "--generate-notes",
                "--title",
                "v0.0.0",
                "--target",
                SHA_A,
            ]
        ]

    def test_includes_notes_start_tag_when_previous_exists(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        seen: list[list[str]] = []

        def fake_run(
            cmd: list[str],
            *,
            check: bool = False,
            capture_output: bool = False,
            text: bool = False,
        ) -> object:
            del check, capture_output, text
            seen.append(cmd)
            return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

        monkeypatch.setattr(rp.subprocess, "run", fake_run)
        rp.create_github_release(
            semver="v0.0.1",
            sha=SHA_B,
            previous_semver="v0.0.0",
            bootstrap=False,
        )
        assert "--notes-start-tag" in seen[0]
        assert "v0.0.0" in seen[0]


class TestLoadSaveRoundTrip:
    def test_round_trip(self, tmp_path: pathlib.Path) -> None:
        path = tmp_path / "release-pointers.json"
        data = _minimal_pointers()
        rp.set_pointer(data, "current", sha=SHA_A, semver="v0.0.0")
        rp.save_pointers(data, path)
        loaded = rp.load_pointers(path)
        assert loaded["pointers"]["current"]["sha"] == SHA_A
        assert json.loads(path.read_text(encoding="utf-8"))["major"] == 0
