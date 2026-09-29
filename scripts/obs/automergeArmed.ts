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
 * (required checks pending), upsert a PR comment so the schedule completer can
 * finish the merge via Vault REST later — independent of CI duration.
 */

const MERGE_READY_LABEL = 'oblt-aw/ai/merge-ready';
const ARMED_COMMENT_MARKER = '<!-- obs-aw-automerge:armed -->';

function buildArmedCommentBody(runUrl) {
  const lines = [
    ARMED_COMMENT_MARKER,
    '',
    'Automerge is **armed** and waiting on required status checks.',
    '',
    'Direct squash-merge was deferred (checks still pending). A dedicated schedule (every 30 minutes) retries merge as the Vault app (CODEOWNERS bypass via classic `pull_request_bypassers`) once GitHub reports all required checks green.',
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
 * List open merge-ready PRs that carry the armed marker (schedule completer).
 * Bounded to labeled open PRs only — not every check event.
 */
async function listArmedMergeReadyPrs({ github, owner, repo, core }) {
  const pulls = await github.paginate(github.rest.pulls.list, {
    owner,
    repo,
    state: 'open',
    per_page: 100,
  });

  const results = [];
  for (const pr of pulls || []) {
    const prNumber = pr.number;
    const labelNames = (pr.labels || []).map((l) => l.name);
    if (!labelNames.includes(MERGE_READY_LABEL)) {
      continue;
    }
    const armed = await prHasArmedMarker({ github, owner, repo, prNumber });
    if (!armed) {
      core.info(`PR #${prNumber}: schedule skip (not armed)`);
      continue;
    }
    const headSha = pr.head?.sha || '';
    if (!headSha) {
      core.info(`PR #${prNumber}: schedule skip (empty head SHA)`);
      continue;
    }
    core.info(`PR #${prNumber}: schedule candidate (head ${headSha})`);
    results.push({ pr_number: String(prNumber), head_sha: headSha });
  }

  core.info(`Automerge complete: ${results.length} armed merge-ready PR(s) for schedule`);
  return results;
}

module.exports.MERGE_READY_LABEL = MERGE_READY_LABEL;
module.exports.ARMED_COMMENT_MARKER = ARMED_COMMENT_MARKER;
module.exports.buildArmedCommentBody = buildArmedCommentBody;
module.exports.findArmedComment = findArmedComment;
module.exports.upsertArmedComment = upsertArmedComment;
module.exports.prHasArmedMarker = prHasArmedMarker;
module.exports.listArmedMergeReadyPrs = listArmedMergeReadyPrs;

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

/**
 * Discover armed merge-ready candidates for the schedule completer.
 * @returns {{ candidates: Array<{ pr_number: string, head_sha: string }> }}
 */
module.exports.runDiscoverCandidates = async function runDiscoverCandidates({
  github,
  context,
  core,
}) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  const candidates = await listArmedMergeReadyPrs({ github, owner, repo, core });
  return { candidates };
};
