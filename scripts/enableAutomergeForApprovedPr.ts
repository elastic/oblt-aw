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

module.exports.run = async function run({ github, context, core, prNumber }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  if (typeof prNumber !== 'number' || !Number.isFinite(prNumber)) {
    core.info('No pull request number for auto-merge enablement.');
    return;
  }

  const { data: pr } = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: prNumber,
  });

  const { data: checkRuns } = await github.rest.checks.listForRef({
    owner,
    repo,
    ref: pr.head.sha,
    per_page: 100,
  });

  const all = checkRuns.check_runs || [];
  const total = all.length;
  const completed = all.filter((check) => check.status === 'completed').length;
  const failedCount = all.filter(
    (check) =>
      check.status === 'completed' &&
      !['success', 'skipped', 'neutral'].includes(check.conclusion || '')
  ).length;

  let checkStatus = 'passing';
  if (total === 0) {
    checkStatus = 'no_checks';
  } else if (completed < total) {
    checkStatus = 'pending';
  } else if (failedCount > 0) {
    checkStatus = 'failing';
  }

  if (checkStatus !== 'passing') {
    core.info(`PR #${prNumber}: skipped - check status is '${checkStatus}'`);
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

  if (pr.auto_merge != null) {
    core.info(`PR #${prNumber}: auto-merge already enabled`);
    return;
  }

  core.info(`PR #${prNumber}: enabling auto-merge (squash)`);
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
  } catch (error) {
    core.warning(`PR #${prNumber}: failed to enable auto-merge`);
    core.warning(String(error));
    throw new Error(`PR #${prNumber} could not have auto-merge enabled`);
  }
};
