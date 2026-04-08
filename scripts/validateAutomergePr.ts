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
 * label, draft/fork/ref rules, and check-runs via GITHUB_TOKEN).
 *
 * Keep ALLOWED_PR_AUTHORS in sync with the `dependency-review` and `automerge` jobs
 * in `.github/workflows/oblt-aw-ingress.yml`.
 */
const MERGE_READY_LABEL = 'oblt-aw/ai/merge-ready';

const ALLOWED_PR_AUTHORS = new Set([
  'dependabot[bot]',
  'renovate[bot]',
  'Dependabot',
  'Renovate',
  'elastic-vault-github-plugin-prod[bot]',
]);

function checkRunGateStatus(checkRuns) {
  const all = checkRuns || [];
  const total = all.length;
  const completed = all.filter((c) => c.status === 'completed').length;
  const failedCount = all.filter(
    (c) =>
      c.status === 'completed' &&
      !['success', 'skipped', 'neutral'].includes(c.conclusion || '')
  ).length;

  if (total === 0) return 'no_checks';
  if (completed < total) return 'pending';
  if (failedCount > 0) return 'failing';
  return 'passing';
}

module.exports.run = async function run({ github, context, prNumber, core }) {
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

  const { data: checkPayload } = await github.rest.checks.listForRef({
    owner,
    repo,
    ref: pr.head.sha,
    per_page: 100,
  });

  const checkStatus = checkRunGateStatus(checkPayload.check_runs || []);
  if (checkStatus !== 'passing') {
    core.info(`PR #${prNumber}: check-runs not ready ('${checkStatus}')`);
    return { ok: false };
  }

  core.info(`PR #${prNumber}: passed automerge validation (including check-runs)`);
  return { ok: true };
};
