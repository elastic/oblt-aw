# catalog-info platform bridge (oblt-aw onboard Phase 2)

Files under this tree are mirrored into [elastic/catalog-info](https://github.com/elastic/catalog-info).

| Path | Purpose |
|------|---------|
| `.github/workflows/oblt-aw-onboard-phase2-bridge.yml` | On merge of `[oblt-aw][onboard]` PRs, check Phase 2 on the linked onboard issue |
| `.github/scripts/oblt-aw-onboard-phase2-bridge/check_phase2.py` | Issue resolution + Phase 2 checkbox PATCH |
| `resources/github-token-policies/token-policy-oblt-aw-onboard-phase2-bridge.yaml` | OIDC TokenPolicy (`issues: write` on `elastic/oblt-aw`) |

Keep catalog-info copies identical to this directory. Phase 1 of `gh-aw-onboard-repository` gap-fills these files when missing.

The Python helper is also mirrored at `scripts/onboard_phase2_bridge.py` (for mypy). Unit tests require those two files to stay byte-identical.
