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
/** @deprecated Prefer detecting any ``<org>:automerge`` parent from the enabled list. */
const AUTOMERGE_PARENT_COMPOUND_ID = 'obs:automerge';
const AUTOMERGE_PARENT_RE = /^([a-z0-9-]+):automerge$/;
const AUTOMERGE_SERVICES_GUIDE_URL =
  'https://codex.elastic.dev/r/oblt-aw/user-guide/automerge-services';
const OPT_IN_OPT_OUT_GUIDE_URL =
  'https://codex.elastic.dev/r/oblt-aw/user-guide/opt-in-opt-out';

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

/**
 * Collect enabled automerge collection ids from any org that has
 * ``<org>:automerge`` checked (common services appear per-org on the dashboard).
 * @param {string[]} enabledWorkflows
 * @param {string} [orgKey] When set, only that org's parent/collections are used.
 * @returns {string[]}
 */
function enabledAutomergeCollectionIds(enabledWorkflows, orgKey) {
  const parents =
    typeof orgKey === 'string' && orgKey
      ? enabledWorkflows.filter((id) => id === `${orgKey}:automerge`)
      : enabledWorkflows.filter((id) => AUTOMERGE_PARENT_RE.test(id));
  if (parents.length === 0) {
    return [];
  }
  const collectionIds = [];
  for (const parent of parents) {
    const match = AUTOMERGE_PARENT_RE.exec(parent);
    if (!match) {
      continue;
    }
    const prefix = `${match[1]}:automerge:`;
    for (const id of enabledWorkflows) {
      if (id.startsWith(prefix)) {
        collectionIds.push(id.slice(prefix.length));
      }
    }
  }
  return [...new Set(collectionIds)];
}

function collectionMatchesAllFiles(collection, files) {
  if (files.length === 0) {
    return false;
  }
  const globs = collection['file-glob'] || [];
  return files.every((file) => pathMatchesAnyGlob(file, globs));
}

/**
 * When several collections cover every changed file, drop any whose file-glob
 * set is a strict superset of another matched collection. That keeps go-only
 * PRs on go-dependencies when update-beats (NOTICE + go + beats) also matches.
 * @param {DependencyCollection[]} matched
 * @returns {DependencyCollection[]}
 */
function preferNonSupersetCollections(matched) {
  return matched.filter((candidate) => {
    const candidateGlobs = new Set(candidate['file-glob'] || []);
    return !matched.some((other) => {
      if (other.id === candidate.id) {
        return false;
      }
      const otherGlobs = other['file-glob'] || [];
      if (otherGlobs.length === 0 || otherGlobs.length >= candidateGlobs.size) {
        return false;
      }
      const otherIsSubset = otherGlobs.every((g) => candidateGlobs.has(g));
      const sameSize = otherGlobs.length === candidateGlobs.size;
      return otherIsSubset && !sameSize;
    });
  });
}

function classifyChangedFiles(files, collections, enabledCollectionIds) {
  const changed = [...new Set(files.map((f) => f.trim()).filter(Boolean))];
  const enabledSet = new Set(enabledCollectionIds);
  if (changed.length === 0) {
    return { status: 'unclassified', collectionId: null };
  }

  const matched = preferNonSupersetCollections(
    collections.filter((c) => collectionMatchesAllFiles(c, changed))
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
  let nextStep =
    `To allow automerge for this kind of update, enable the matching collection under Automerge on the Control Plane Dashboard (the \`oblt-aw/dashboard\` issue). See [Automerge dependency collections](${AUTOMERGE_SERVICES_GUIDE_URL}) for what each collection covers.`;
  if (outcome.status === 'disabled') {
    reason = `Automerge skipped this pull request because the **\`${outcome.collectionId}\`** collection is not enabled for this repository.`;
  } else if (outcome.status === 'unclassified') {
    reason =
      'Automerge skipped this pull request because the changed files do not match any configured dependency collection.';
    nextStep =
      'If this update should be automerged, ask a maintainer to add or adjust a collection, or merge the pull request manually.';
  } else if (outcome.status === 'ambiguous') {
    reason = `Automerge skipped this pull request because the changed files matched more than one collection: ${outcome.collectionIds.map((id) => `\`${id}\``).join(', ')}.`;
    nextStep =
      'Narrow the change to a single dependency type, or ask a maintainer to merge the pull request manually.';
  }

  return [
    GATE_COMMENT_MARKER,
    '',
    '### Automerge skipped',
    '',
    reason,
    '',
    nextStep,
    '',
    `See [Opt in or opt out](${OPT_IN_OPT_OUT_GUIDE_URL}) for how to enable or disable Automerge collections on the Control Plane Dashboard.`,
    '',
    `Collections currently enabled for automerge: ${enabledList}`,
    '',
    'Changed files considered:',
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
