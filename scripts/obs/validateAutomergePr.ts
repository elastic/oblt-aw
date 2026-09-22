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
 * Allowed authors are defined only in `config/obs/allowed_pr_authors.json` (Observability
 * control-plane). Prelude loads that file into CSV/JSON for ingress and
 * `allowed-bot-users`; do not duplicate the list in workflow prompts.
 *
 * GraphQL/`gh pr view` (gh ≥ 2.50) may return `app/<slug>` for GitHub Apps while REST
 * and webhooks return `<slug>[bot]`. Matching always normalizes `app/<slug>` →
 * `<slug>[bot]` before comparing to the JSON allow list.
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

/**
 * Map GraphQL app actor logins to the REST/`…[bot]` form used in allowed_pr_authors.json.
 * Leave other logins unchanged (including human Dependabot/Renovate display names).
 */
function normalizePrAuthorLogin(login) {
  const raw = String(login || '').trim();
  if (!raw) {
    return '';
  }
  const appMatch = /^app\/([^/]+)$/i.exec(raw);
  if (appMatch) {
    return `${appMatch[1]}[bot]`;
  }
  return raw;
}

function isAllowedPrAuthor(login) {
  return ALLOWED_PR_AUTHORS.has(normalizePrAuthorLogin(login));
}

module.exports.normalizePrAuthorLogin = normalizePrAuthorLogin;
module.exports.isAllowedPrAuthor = isAllowedPrAuthor;

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

  const authorRaw = pr.user?.login || '';
  const author = normalizePrAuthorLogin(authorRaw);
  if (!ALLOWED_PR_AUTHORS.has(author)) {
    core.info(
      `PR #${prNumber}: author '${authorRaw}'` +
        (author !== authorRaw ? ` (normalized '${author}')` : '') +
        ' is not in the automerge allow list'
    );
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
