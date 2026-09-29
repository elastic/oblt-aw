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
 * Squash-merge a PR via the REST merge API (Vault-app token when used from
 * automerge jobs). Classifies pending required checks so the schedule completer can
 * no-op cleanly until CI is green.
 */

function extractErrorMessage(err) {
  if (!err) {
    return '';
  }
  const responseMsg = err.response?.data?.message;
  if (typeof responseMsg === 'string' && responseMsg.trim()) {
    return responseMsg.trim();
  }
  if (typeof err.message === 'string') {
    return err.message.trim();
  }
  return String(err);
}

function classifyMergeError(err) {
  const status = err?.status ?? err?.response?.status;
  const message = extractErrorMessage(err);
  const lower = message.toLowerCase();

  if (status === 405 && /already been merged|pull request is not open/i.test(message)) {
    return { result: 'merged', message };
  }
  if (
    status === 405 &&
    (/required status check/i.test(message) ||
      /\bpending\b/i.test(lower) ||
      /not mergeable/i.test(lower))
  ) {
    return { result: 'pending_checks', message };
  }
  if (status === 409) {
    return { result: 'sha_mismatch', message };
  }
  return { result: 'failed', message };
}

/**
 * @returns {{ result: 'merged' | 'pending_checks' | 'sha_mismatch' | 'failed', message?: string }}
 */
async function mergePullRequestRest({ github, owner, repo, prNumber, headSha, core }) {
  try {
    await github.rest.pulls.merge({
      owner,
      repo,
      pull_number: prNumber,
      merge_method: 'squash',
      sha: headSha,
    });
    core.info(`PR #${prNumber}: merged via REST squash (sha ${headSha})`);
    return { result: 'merged' };
  } catch (err) {
    const classified = classifyMergeError(err);
    core.info(
      `PR #${prNumber}: REST merge result=${classified.result}` +
        (classified.message ? ` (${classified.message})` : '')
    );
    return classified;
  }
}

module.exports.extractErrorMessage = extractErrorMessage;
module.exports.classifyMergeError = classifyMergeError;
module.exports.mergePullRequestRest = mergePullRequestRest;

module.exports.run = async function run({
  github,
  context,
  prNumber,
  headSha,
  core,
}) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;
  if (typeof prNumber !== 'number' || !Number.isFinite(prNumber)) {
    core.info('Automerge REST merge: invalid PR number; skipping.');
    return { result: 'failed', message: 'invalid pr number' };
  }
  const sha = String(headSha || '').trim();
  if (!sha) {
    core.info('Automerge REST merge: empty head SHA; skipping.');
    return { result: 'failed', message: 'empty head sha' };
  }
  return mergePullRequestRest({ github, owner, repo, prNumber, headSha: sha, core });
};
