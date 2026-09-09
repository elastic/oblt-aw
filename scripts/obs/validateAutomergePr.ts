// Copyright 2026-2027 Elasticsearch B.V.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

/**
 * Validates the triggering pull request for automerge (author allow list, merge-ready
 * label, draft/fork/ref rules, and non-empty shared-token-policy when the author is
 * github-actions[bot] so approve can use Vault instead of self-APPROVE). Required status
 * checks are enforced by GitHub when auto-merge is enabled, not here.
 *
 * Allowed authors are defined in `config/obs/allowed_pr_authors.json` (Observability
 * control-plane; also reflected in `obs-aw-automerge.yml` via
 * `load-allowed-authors` and `obs-aw-dependency-review.yml` (CSV input from the same
 * loader), which cannot load that file in expressions). Specialized issue triage/fixer
 * wrappers (security, resource-not-accessible) pass `allowed_issue_authors_csv` from
 * `config/obs/allowed_issue_authors.json` via the same loader; generic `obs-aw-issue-triage`
 * / `obs-aw-issue-fixer` do not.
 */
const path = require('node:path');
const fs = require('node:fs');

const MERGE_READY_LABEL = 'oblt-aw/ai/merge-ready';
const GITHUB_ACTIONS_BOT = 'github-actions[bot]';

const ALLOWED_PR_AUTHORS = new Set(
  JSON.parse(
    fs.readFileSync(
      path.join(__dirname, '..', '..', 'config', 'obs', 'allowed_pr_authors.json'),
      'utf8'
    )
  )
);

module.exports.run = async function run({
  github,
  context,
  prNumber,
  core,
  sharedTokenPolicy = '',
}) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  if (typeof prNumber !== 'number' || !Number.isFinite(prNumber)) {
    core.info('Automerge: invalid or missing pull request number; skipping.');
    return { ok: false };
  }

  const { data: pr } = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: prNumber,
  });

  const author = pr.user?.login || '';
  if (!ALLOWED_PR_AUTHORS.has(author)) {
    core.info(`PR #${prNumber}: author '${author}' is not in the automerge allow list`);
    return { ok: false };
  }

  // Approve must use Vault for github-actions-authored PRs (GITHUB_TOKEN would self-APPROVE).
  if (author === GITHUB_ACTIONS_BOT && !(sharedTokenPolicy || '').trim()) {
    core.info(
      `PR #${prNumber}: author '${GITHUB_ACTIONS_BOT}' requires a non-empty shared-token-policy so approve can use Vault instead of GITHUB_TOKEN`
    );
    return { ok: false };
  }

  const labelNames = (pr.labels || []).map((l) => l.name);
  if (!labelNames.includes(MERGE_READY_LABEL)) {
    core.info(`PR #${prNumber}: missing label '${MERGE_READY_LABEL}'`);
    return { ok: false };
  }

  if (pr.draft) {
    core.info(`PR #${prNumber}: draft PRs are excluded`);
    return { ok: false };
  }

  const headFull = pr.head?.repo?.full_name || '';
  const baseFull = pr.base?.repo?.full_name || '';
  if (headFull !== baseFull) {
    core.info(`PR #${prNumber}: fork PRs are excluded`);
    return { ok: false };
  }

  if ((pr.head?.ref || '') === (pr.base?.ref || '')) {
    core.info(`PR #${prNumber}: head ref equals base ref`);
    return { ok: false };
  }

  core.info(`PR #${prNumber}: passed automerge validation`);
  return { ok: true };
};
