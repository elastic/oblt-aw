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

const GATE_COMMENT_MARKER = '<!-- oblt-aw-automerge:dependency-collection-gate -->';

/** @typedef {object} DependencyCollection
 * @property {string} id
 * @property {string} [description]
 * @property {boolean} active
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

/** @typedef {object} ClassificationOutcomeInactive
 * @property {'inactive'} status
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

/** @typedef {ClassificationOutcomeAllowed|ClassificationOutcomeInactive|ClassificationOutcomeUnclassified|ClassificationOutcomeAmbiguous} ClassificationOutcome
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

function activeCollectionIds(collections) {
  return collections.filter((c) => c.active).map((c) => c.id);
}

function collectionMatchesAllFiles(collection, files) {
  if (files.length === 0) {
    return false;
  }
  const globs = collection['file-glob'] || [];
  return files.every((file) => pathMatchesAnyGlob(file, globs));
}

function classifyChangedFiles(files, collections) {
  const changed = [...new Set(files.map((f) => f.trim()).filter(Boolean))];
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
  if (collection.active) {
    return { status: 'allowed', collectionId: collection.id };
  }
  return { status: 'inactive', collectionId: collection.id };
}

function buildGateCommentBody(outcome, changedFiles, activeIds) {
  const activeList =
    activeIds.length > 0
      ? activeIds.map((id) => `\`${id}\``).join(', ')
      : '_(none configured)_';
  const fileSample = changedFiles.slice(0, 20);
  const fileLines = fileSample.map((f) => `- \`${f}\``).join('\n');
  const fileSuffix =
    changedFiles.length > fileSample.length
      ? `\n- _…and ${changedFiles.length - fileSample.length} more_`
      : '';

  let reason = '';
  if (outcome.status === 'inactive') {
    reason = `This pull request was classified as **\`${outcome.collectionId}\`**. The Observability automerge workflow does not support that dependency collection.`;
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
    `**Collections enabled for automerge:** ${activeList}`,
    '',
    'Dependency-review may still have applied `oblt-aw/ai/merge-ready` for risk review. Only allow-listed collections proceed to Copilot approval and merge via this workflow.',
    '',
    '**Changed files considered for classification:**',
    fileLines || '- _(none)_',
    fileSuffix,
  ].join('\n');
}

module.exports = {
  GATE_COMMENT_MARKER,
  loadCollectionsConfig,
  activeCollectionIds,
  classifyChangedFiles,
  buildGateCommentBody,
};
