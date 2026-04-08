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
 * Drop check runs created by the current GitHub Actions workflow run so the
 * automerge gate does not wait on itself. Other checks on the same commit
 * still gate verification; when they finish, the workflow runs again and can pass.
 */
function filterCheckRunsExcludingCurrentWorkflow(checkRuns, currentRunId) {
  const all = checkRuns || [];
  if (typeof currentRunId !== 'number' || !Number.isFinite(currentRunId)) {
    return all;
  }
  const marker = `/runs/${currentRunId}/`;
  return all.filter((c) => {
    const url = c.details_url || '';
    return !url.includes(marker);
  });
}

function checkRunGateStatus(checkRuns, currentRunId) {
  const all = filterCheckRunsExcludingCurrentWorkflow(checkRuns, currentRunId);
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

module.exports = {
  filterCheckRunsExcludingCurrentWorkflow,
  checkRunGateStatus,
};
