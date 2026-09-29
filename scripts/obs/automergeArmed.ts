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
 * Automerge "armed" marker helpers: when the PR path cannot squash-merge yet
 * (required checks pending), upsert a PR comment so the status-success path can
 * complete the merge via Vault REST later — independent of CI duration.
 */

const MERGE_READY_LABEL = 'oblt-aw/ai/merge-ready';
const ARMED_COMMENT_MARKER = '<!-- obs-aw-automerge:armed -->';

function buildArmedCommentBody(runUrl) {
  const lines = [
    ARMED_COMMENT_MARKER,
    '',
    'Automerge is **armed** and waiting on required status checks.',
    '',
    'Direct squash-merge was deferred (checks still pending). When required CI reports success, a status-triggered merge will retry as the Vault app (CODEOWNERS bypass via classic `pull_request_bypassers`).',
    '',
    'This path does not rely on GitHub native `--auto` merge for completion.',
  ];
  if (runUrl) {
    lines.push('', `Armed by workflow run: ${runUrl}`);
  }
  return lines.join('\n');
}

async function findArmedComment(github, owner, repo, prNumber) {
  const comments = await github.paginate(github.rest.issues.listComments, {
    owner,
    repo,
    issue_number: prNumber,
  });
  return comments.find((c) => (c.body || '').includes(ARMED_COMMENT_MARKER)) || null;
}

async function upsertArmedComment({ github, owner, repo, prNumber, runUrl, core }) {
  const body = buildArmedCommentBody(runUrl || '');
  const existing = await findArmedComment(github, owner, repo, prNumber);
  if (existing) {
    await github.rest.issues.updateComment({
      owner,
      repo,
      comment_id: existing.id,
      body,
    });
    core.info(`PR #${prNumber}: updated automerge armed comment`);
    return { created: false, commentId: existing.id };
  }
  const { data } = await github.rest.issues.createComment({
    owner,
    repo,
    issue_number: prNumber,
    body,
  });
  core.info(`PR #${prNumber}: created automerge armed comment`);
  return { created: true, commentId: data.id };
}

async function prHasArmedMarker({ github, owner, repo, prNumber }) {
  const existing = await findArmedComment(github, owner, repo, prNumber);
  return Boolean(existing);
}

/**
 * Find an open merge-ready PR for a commit SHA that was armed on the PR path.
 * Prefers PRs whose head SHA equals the status SHA.
 */
async function findArmedMergeReadyPrForSha({ github, owner, repo, sha, core }) {
  const commitSha = String(sha || '').trim();
  if (!commitSha) {
    core.info('Automerge complete: empty status SHA; skipping.');
    return { prNumber: null, headSha: '' };
  }

  const { data: associated } = await github.rest.repos.listPullRequestsAssociatedWithCommit({
    owner,
    repo,
    commit_sha: commitSha,
  });

  const candidates = (associated || []).filter((pr) => pr.state === 'open');
  if (candidates.length === 0) {
    core.info(`Automerge complete: no open PR associated with ${commitSha}`);
    return { prNumber: null, headSha: '' };
  }

  // Prefer exact head SHA match, then other open associated PRs.
  const ordered = [
    ...candidates.filter((pr) => (pr.head?.sha || '') === commitSha),
    ...candidates.filter((pr) => (pr.head?.sha || '') !== commitSha),
  ];

  for (const pr of ordered) {
    const prNumber = pr.number;
    const labelNames = (pr.labels || []).map((l) => l.name);
    if (!labelNames.includes(MERGE_READY_LABEL)) {
      core.info(`PR #${prNumber}: skip (missing ${MERGE_READY_LABEL})`);
      continue;
    }
    const armed = await prHasArmedMarker({ github, owner, repo, prNumber });
    if (!armed) {
      core.info(`PR #${prNumber}: skip (not armed)`);
      continue;
    }
    const headSha = pr.head?.sha || commitSha;
    core.info(`PR #${prNumber}: selected for status-complete merge (head ${headSha})`);
    return { prNumber, headSha };
  }

  core.info(`Automerge complete: no armed merge-ready open PR for ${commitSha}`);
  return { prNumber: null, headSha: '' };
}

module.exports.MERGE_READY_LABEL = MERGE_READY_LABEL;
module.exports.ARMED_COMMENT_MARKER = ARMED_COMMENT_MARKER;
module.exports.buildArmedCommentBody = buildArmedCommentBody;
module.exports.findArmedComment = findArmedComment;
module.exports.upsertArmedComment = upsertArmedComment;
module.exports.prHasArmedMarker = prHasArmedMarker;
module.exports.findArmedMergeReadyPrForSha = findArmedMergeReadyPrForSha;

module.exports.runUpsertArmed = async function runUpsertArmed({
  github,
  context,
  prNumber,
  core,
  runUrl = '',
}) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  if (typeof prNumber !== 'number' || !Number.isFinite(prNumber)) {
    core.info('Automerge arm: invalid PR number; skipping.');
    return { ok: false };
  }
  await upsertArmedComment({ github, owner, repo, prNumber, runUrl, core });
  return { ok: true };
};

module.exports.runFindForStatus = async function runFindForStatus({
  github,
  context,
  sha,
  core,
}) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  return findArmedMergeReadyPrForSha({ github, owner, repo, sha, core });
};
