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

const path = require('node:path');
const fs = require('node:fs');

const { pathMatchesAnyGlob } = require('./lib/matchPathGlob.ts');

const GATE_COMMENT_MARKER = '<!-- obs-aw-automerge:dependency-collection-gate -->';
const AUTOMERGE_PARENT_COMPOUND_ID = 'obs:automerge';

/** @typedef {object} DependencyCollection
 * @property {string} id
 * @property {string} [description]
 * @property {string[]} file-glob
 */

/** @typedef {object} CollectionsConfig
 * @property {number} version
 * @property {string} policy
 * @property {DependencyCollection[]} collections
 */

/** @typedef {object} ClassificationOutcomeAllowed
 * @property {'allowed'} status
 * @property {string} collectionId
 */

/** @typedef {object} ClassificationOutcomeDisabled
 * @property {'disabled'} status
 * @property {string} collectionId
 */

/** @typedef {object} ClassificationOutcomeUnclassified
 * @property {'unclassified'} status
 * @property {null} collectionId
 */

/** @typedef {object} ClassificationOutcomeAmbiguous
 * @property {'ambiguous'} status
 * @property {string[]} collectionIds
 */

/** @typedef {ClassificationOutcomeAllowed|ClassificationOutcomeDisabled|ClassificationOutcomeUnclassified|ClassificationOutcomeAmbiguous} ClassificationOutcome
 */

const CONFIG_PATH = path.join(
  __dirname,
  '..',
  '..',
  'config',
  'obs',
  'automerge-dependency-collections.json'
);

function loadCollectionsConfig(configPath = CONFIG_PATH) {
  return JSON.parse(fs.readFileSync(configPath, 'utf8'));
}

function parseEnabledWorkflowsJson(raw) {
  if (!raw || typeof raw !== 'string' || !raw.trim()) {
    return [];
  }
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed)
      ? parsed.filter((item) => typeof item === 'string')
      : [];
  } catch {
    return [];
  }
}

function enabledAutomergeCollectionIds(enabledWorkflows, orgKey = 'obs') {
  if (!enabledWorkflows.includes(AUTOMERGE_PARENT_COMPOUND_ID)) {
    return [];
  }
  const prefix = `${orgKey}:automerge:`;
  return enabledWorkflows
    .filter((id) => id.startsWith(prefix))
    .map((id) => id.slice(prefix.length));
}

function collectionMatchesAllFiles(collection, files) {
  if (files.length === 0) {
    return false;
  }
  const globs = collection['file-glob'] || [];
  return files.every((file) => pathMatchesAnyGlob(file, globs));
}

function classifyChangedFiles(files, collections, enabledCollectionIds) {
  const changed = [...new Set(files.map((f) => f.trim()).filter(Boolean))];
  const enabledSet = new Set(enabledCollectionIds);
  if (changed.length === 0) {
    return { status: 'unclassified', collectionId: null };
  }

  const matched = collections.filter((c) =>
    collectionMatchesAllFiles(c, changed)
  );

  if (matched.length === 0) {
    return { status: 'unclassified', collectionId: null };
  }
  if (matched.length > 1) {
    return {
      status: 'ambiguous',
      collectionIds: matched.map((c) => c.id),
    };
  }

  const collection = matched[0];
  if (enabledSet.has(collection.id)) {
    return { status: 'allowed', collectionId: collection.id };
  }
  return { status: 'disabled', collectionId: collection.id };
}

function buildGateCommentBody(outcome, changedFiles, enabledCollectionIds) {
  const enabledList =
    enabledCollectionIds.length > 0
      ? enabledCollectionIds.map((id) => `\`${id}\``).join(', ')
      : '_(none enabled on the Control Plane Dashboard)_';
  const fileSample = changedFiles.slice(0, 20);
  const fileLines = fileSample.map((f) => `- \`${f}\``).join('\n');
  const fileSuffix =
    changedFiles.length > fileSample.length
      ? `\n- _…and ${changedFiles.length - fileSample.length} more_`
      : '';

  let reason = '';
  if (outcome.status === 'disabled') {
    reason = `This pull request was classified as **\`${outcome.collectionId}\`**, but that dependency collection is not enabled on the Control Plane Dashboard for this repository.`;
  } else if (outcome.status === 'unclassified') {
    reason =
      'This pull request could not be matched to any configured dependency collection from its changed files.';
  } else if (outcome.status === 'ambiguous') {
    reason = `This pull request matched multiple dependency collections: ${outcome.collectionIds.map((id) => `\`${id}\``).join(', ')}. Automerge requires an unambiguous classification.`;
  }

  return [
    GATE_COMMENT_MARKER,
    '',
    '### Automerge skipped (dependency collection)',
    '',
    reason,
    '',
    `**Collections enabled for automerge on this repository:** ${enabledList}`,
    '',
    'Enable or disable collections under the Automerge workflow on the Control Plane Dashboard (`oblt-aw/dashboard` issue). Dependency-review may still have applied `oblt-aw/ai/merge-ready` for risk review. Only enabled collections proceed to Copilot approval and merge via this workflow.',
    '',
    '**Changed files considered for classification:**',
    fileLines || '- _(none)_',
    fileSuffix,
  ].join('\n');
}

module.exports = {
  GATE_COMMENT_MARKER,
  AUTOMERGE_PARENT_COMPOUND_ID,
  loadCollectionsConfig,
  parseEnabledWorkflowsJson,
  enabledAutomergeCollectionIds,
  classifyChangedFiles,
  buildGateCommentBody,
};
