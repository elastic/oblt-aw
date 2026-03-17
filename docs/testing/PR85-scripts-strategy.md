# Testing Strategy: PR 85 Scripts

## Scope

Unit tests for the Python scripts introduced in [PR 85](https://github.com/elastic/oblt-aw/pull/85) (sync-control-plane-dashboard workflow):

- `scripts/sync_control_plane_dashboard.py`
- `scripts/build_repos_matrix.py`

## Test Files

| Script | Test File | Coverage |
|--------|-----------|----------|
| sync_control_plane_dashboard.py | tests/test_sync_control_plane_dashboard.py | parse_checkbox_state, maturity_badge, build_dashboard_body |
| build_repos_matrix.py | tests/test_build_repos_matrix.py | parse_repositories, write_outputs, main() |

## Risk Areas Addressed

1. **Checkbox parsing** — Same format as TS `parseDashboardBody`; tests mirror TS cases (all checked, all unchecked, mixed, malformed, long IDs).
2. **Maturity badges** — All known values (stable, early-adoption, experimental) and unknown fallback.
3. **Dashboard body building** — Defaults, user state preservation, default_enabled behavior.
4. **Repository parsing** — List/dict formats, deduplication, validation, error paths.
5. **GITHUB_OUTPUT** — Write behavior and env requirement.

## Execution

```bash
pytest tests/test_sync_control_plane_dashboard.py tests/test_build_repos_matrix.py -v --tb=short
```

## Known Gaps

- `gh_api`, `find_dashboard_issue`, `create_issue`, `update_issue`, `pin_issue`, `sync_repo` in sync_control_plane_dashboard.py require network/gh CLI; not unit-tested. Integration tests would cover these.
- Uppercase `[X]` in checkboxes is not supported by the regex `[ x]`; only lowercase `[x]` matches.

## Related

- Related issue: https://github.com/elastic/observability-robots/issues/3762
- PR 85: https://github.com/elastic/oblt-aw/pull/85
