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
 * Classifies a dependency-update PR by changed file paths (no extra repo labels),
 * allows automerge only for dashboard-enabled collections, and posts or removes a
 * single gate comment on the PR when automerge is skipped.
 */
const {
  GATE_COMMENT_MARKER,
  buildGateCommentBody,
  classifyChangedFiles,
  enabledAutomergeCollectionIds,
  loadCollectionsConfig,
  parseEnabledWorkflowsJson,
} = require('./classifyAutomergeDependencyCollection.ts');
const { parseAutomergePolicyJson } = require('./automergePolicy.ts');

/**
 * @param {import('@octokit/rest').Octokit} github
 * @param {string} owner
 * @param {string} repo
 * @param {number} prNumber
 * @returns {Promise<{ filename: string, previous_filename?: string }[]>}
 */
async function listPullRequestFiles(github, owner, repo, prNumber) {
  const files = await github.paginate(github.rest.pulls.listFiles, {
    owner,
    repo,
    pull_number: prNumber,
  });
  return files.map((f) => ({
    filename: f.filename,
    previous_filename: f.previous_filename || undefined,
  }));
}

/**
 * Current names for collection matching, plus previous names for path policy.
 * @param {{ filename: string, previous_filename?: string }[]} files
 * @returns {{ filenames: string[], pathPolicyNames: string[] }}
 */
function splitFileNamesForGates(files) {
  /** @type {string[]} */
  const filenames = [];
  /** @type {string[]} */
  const pathPolicyNames = [];
  for (const file of files) {
    if (typeof file.filename === 'string' && file.filename) {
      filenames.push(file.filename);
      pathPolicyNames.push(file.filename);
    }
    if (
      typeof file.previous_filename === 'string' &&
      file.previous_filename
    ) {
      pathPolicyNames.push(file.previous_filename);
    }
  }
  return { filenames, pathPolicyNames };
}

async function findGateComment(github, owner, repo, prNumber) {
  const comments = await github.paginate(github.rest.issues.listComments, {
    owner,
    repo,
    issue_number: prNumber,
  });
  return comments.find((c) => (c.body || '').includes(GATE_COMMENT_MARKER)) || null;
}

async function upsertGateComment(github, owner, repo, prNumber, body) {
  const existing = await findGateComment(github, owner, repo, prNumber);
  if (existing) {
    if ((existing.body || '').trim() === body.trim()) {
      return;
    }
    await github.rest.issues.updateComment({
      owner,
      repo,
      comment_id: existing.id,
      body,
    });
    return;
  }
  await github.rest.issues.createComment({
    owner,
    repo,
    issue_number: prNumber,
    body,
  });
}

async function removeGateCommentIfPresent(github, owner, repo, prNumber) {
  const existing = await findGateComment(github, owner, repo, prNumber);
  if (!existing) {
    return;
  }
  await github.rest.issues.deleteComment({
    owner,
    repo,
    comment_id: existing.id,
  });
}

module.exports.run = async function run({
  github,
  context,
  prNumber,
  core,
  enabledWorkflowsJson = '[]',
  orgKey = '',
  policyJson = '',
}) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  if (typeof prNumber !== 'number' || !Number.isFinite(prNumber)) {
    core.info('Automerge collection gate: invalid PR number; skipping.');
    return { allowed: false, collectionId: '' };
  }

  // Released tip-from-main helpers must receive the resolved policy JSON object
  // (including defaults). An omitted/blank value must not widen to unrestricted.
  if (!policyJson || typeof policyJson !== 'string' || !policyJson.trim()) {
    core.info(
      'Automerge collection gate: missing automerge policy JSON; denying.'
    );
    return { allowed: false, collectionId: '' };
  }

  let pathPolicy = { allow: [], deny: [] };
  try {
    pathPolicy = parseAutomergePolicyJson(policyJson).paths;
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    core.info(
      `Automerge collection gate: invalid automerge policy (${message}); denying.`
    );
    return { allowed: false, collectionId: '' };
  }

  const config = loadCollectionsConfig();
  const collections = config.collections || [];
  const enabledWorkflows = parseEnabledWorkflowsJson(enabledWorkflowsJson);
  // Tip callers pass shared-org-key. Released @v0 paths omit it; the helper
  // defaults blank/omitted keys to obs (same scope as main before multi-org).
  const enabledCollectionIds = enabledAutomergeCollectionIds(
    enabledWorkflows,
    typeof orgKey === 'string' ? orgKey : undefined
  );

  const { data: pr } = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: prNumber,
  });
  const expectedChangedFiles = Number(pr.changed_files);
  const listedFiles = await listPullRequestFiles(
    github,
    owner,
    repo,
    prNumber
  );
  // GitHub caps pulls.listFiles at 3000 entries even with pagination.
  if (
    Number.isFinite(expectedChangedFiles) &&
    listedFiles.length !== expectedChangedFiles
  ) {
    core.info(
      `PR #${prNumber}: listed ${listedFiles.length} files but PR reports ` +
        `${expectedChangedFiles} changed_files; denying (incomplete file list).`
    );
    return { allowed: false, collectionId: '' };
  }

  const { filenames, pathPolicyNames } = splitFileNamesForGates(listedFiles);
  const outcome = classifyChangedFiles(
    filenames,
    collections,
    enabledCollectionIds,
    pathPolicy,
    pathPolicyNames
  );

  if (outcome.status === 'allowed') {
    core.info(
      `PR #${prNumber}: dependency collection '${outcome.collectionId}' is enabled for automerge`
    );
    await removeGateCommentIfPresent(github, owner, repo, prNumber);
    return { allowed: true, collectionId: outcome.collectionId };
  }

  const collectionId =
    outcome.status === 'ambiguous'
      ? outcome.collectionIds.join(',')
      : outcome.collectionId || '';

  const commentBody = buildGateCommentBody(
    outcome,
    filenames,
    enabledCollectionIds
  );
  await upsertGateComment(github, owner, repo, prNumber, commentBody);

  if (outcome.status === 'disabled') {
    core.info(
      `PR #${prNumber}: collection '${outcome.collectionId}' is not enabled on the dashboard; posted gate comment`
    );
  } else if (outcome.status === 'ambiguous') {
    core.info(
      `PR #${prNumber}: ambiguous collections [${outcome.collectionIds.join(', ')}]; posted gate comment`
    );
  } else if (outcome.status === 'paths-ineligible') {
    core.info(
      `PR #${prNumber}: all-files path policy rejected changed files; posted gate comment`
    );
  } else {
    core.info(
      `PR #${prNumber}: unclassified dependency collection; posted gate comment`
    );
  }

  return { allowed: false, collectionId };
};

module.exports.listPullRequestFiles = listPullRequestFiles;
module.exports.splitFileNamesForGates = splitFileNamesForGates;
