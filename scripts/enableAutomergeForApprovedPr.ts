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
 * GitHub may reject enablePullRequestAutoMerge with "Pull request is in unstable status"
 * while mergeability or checks are still settling after review. Retries with backoff
 * cover that race (see env AUTOMERGE_STABLE_POLL_MS, AUTOMERGE_STABLE_MAX_ATTEMPTS).
 */

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function graphqlErrorText(error) {
  if (error && typeof error === 'object' && 'errors' in error) {
    const errs = error.errors;
    if (Array.isArray(errs)) {
      return errs.map((e) => (e && e.message) || '').join('; ');
    }
  }
  return error instanceof Error ? error.message : String(error);
}

function isUnstableAutomergeError(error) {
  return /unstable status/i.test(graphqlErrorText(error));
}

function readNonNegativeInt(envValue, defaultValue) {
  if (envValue === undefined || envValue === '') {
    return defaultValue;
  }
  const n = Number.parseInt(envValue, 10);
  return Number.isFinite(n) && n >= 0 ? n : defaultValue;
}

function readPositiveIntMin1(envValue, defaultValue) {
  if (envValue === undefined || envValue === '') {
    return defaultValue;
  }
  const n = Number.parseInt(envValue, 10);
  return Number.isFinite(n) && n >= 1 ? n : defaultValue;
}

module.exports.run = async function run({ github, context, core, prNumber }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  const pollMs = readNonNegativeInt(process.env.AUTOMERGE_STABLE_POLL_MS, 20000);
  const maxAttempts = readPositiveIntMin1(process.env.AUTOMERGE_STABLE_MAX_ATTEMPTS, 30);

  if (typeof prNumber !== 'number' || !Number.isFinite(prNumber)) {
    core.info('No pull request number for auto-merge enablement.');
    return;
  }

  const { data: reviews } = await github.rest.pulls.listReviews({
    owner,
    repo,
    pull_number: prNumber,
    per_page: 100,
  });

  const approvedByActions = reviews.some(
    (review) => review.state === 'APPROVED' && review.user?.login === 'github-actions[bot]'
  );

  if (!approvedByActions) {
    core.info(`PR #${prNumber}: skipped - no APPROVED review from github-actions[bot]`);
    return;
  }

  core.info(`PR #${prNumber}: enabling auto-merge (squash)`);

  for (let attempt = 1; attempt <= maxAttempts; attempt++) {
    const { data: pr } = await github.rest.pulls.get({
      owner,
      repo,
      pull_number: prNumber,
    });

    if (pr.auto_merge != null) {
      core.info(`PR #${prNumber}: auto-merge already enabled`);
      return;
    }

    if (pr.mergeable_state === 'dirty') {
      throw new Error(
        `PR #${prNumber} could not have auto-merge enabled: merge conflicts (mergeable_state: dirty)`
      );
    }

    try {
      await github.graphql(
        `mutation EnablePullRequestAutoMerge($pullRequestId: ID!) {
          enablePullRequestAutoMerge(input: {pullRequestId: $pullRequestId, mergeMethod: SQUASH}) {
            clientMutationId
          }
        }`,
        { pullRequestId: pr.node_id }
      );
      core.info(`PR #${prNumber}: auto-merge enabled`);
      return;
    } catch (error) {
      const recoverable = isUnstableAutomergeError(error);
      if (!recoverable || attempt === maxAttempts) {
        core.warning(`PR #${prNumber}: failed to enable auto-merge`);
        core.warning(String(error));
        throw new Error(`PR #${prNumber} could not have auto-merge enabled`);
      }
      core.info(
        `PR #${prNumber}: merge still unstable for auto-merge (attempt ${attempt}/${maxAttempts}); waiting ${pollMs}ms`
      );
      await sleep(pollMs);
    }
  }
};
