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
 * Consumer automerge policy from ``x-oblt-aw.<org>.workflows.automerge.policy``.
 *
 * Defaults match today's behavior: merge-ready only, forks disabled, authors
 * allow-list (control-plane bots only unless the repo adds names).
 */

const MERGE_READY_LABEL = 'oblt-aw/ai/merge-ready';

/** @typedef {'disabled' | 'author-association'} ForksMode */
/** @typedef {'allow-list' | 'author-association'} AuthorsMode */

/** @typedef {object} AutomergePolicy
 * @property {string[]} triggerLabels
 * @property {{ mode: ForksMode, authorAssociations: string[] }} forks
 * @property {{ mode: AuthorsMode, allowList: string[], authorAssociations: string[] }} authors
 */

/**
 * @returns {AutomergePolicy}
 */
function defaultAutomergePolicy() {
  return {
    triggerLabels: [MERGE_READY_LABEL],
    forks: {
      mode: 'disabled',
      authorAssociations: [],
    },
    authors: {
      mode: 'allow-list',
      allowList: [],
      authorAssociations: [],
    },
  };
}

/**
 * @param {unknown} value
 * @returns {string[]}
 */
function asStringList(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return [
    ...new Set(
      value
        .filter((item) => typeof item === 'string')
        .map((item) => item.trim())
        .filter(Boolean)
    ),
  ];
}

/**
 * Normalize a raw policy mapping (kebab-case from apm.yml or camelCase JSON).
 * Always includes ``oblt-aw/ai/merge-ready`` in trigger labels.
 * @param {unknown} raw
 * @returns {AutomergePolicy}
 */
function normalizeAutomergePolicy(raw) {
  const base = defaultAutomergePolicy();
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    return base;
  }
  /** @type {Record<string, unknown>} */
  const obj = /** @type {Record<string, unknown>} */ (raw);

  const triggerRaw = obj['trigger-labels'] ?? obj.triggerLabels;
  const extraLabels = asStringList(triggerRaw);
  const triggerLabels = [
    ...new Set([MERGE_READY_LABEL, ...extraLabels]),
  ];

  const forksRaw = obj.forks;
  /** @type {ForksMode} */
  let forksMode = 'disabled';
  let forksAssociations = [];
  if (forksRaw && typeof forksRaw === 'object' && !Array.isArray(forksRaw)) {
    /** @type {Record<string, unknown>} */
    const forks = /** @type {Record<string, unknown>} */ (forksRaw);
    const mode = forks.mode;
    if (mode === 'author-association' || mode === 'disabled') {
      forksMode = mode;
    }
    forksAssociations = asStringList(
      forks['author-associations'] ?? forks.authorAssociations
    );
  }

  const authorsRaw = obj.authors;
  /** @type {AuthorsMode} */
  let authorsMode = 'allow-list';
  let authorsAllowList = [];
  let authorsAssociations = [];
  if (authorsRaw && typeof authorsRaw === 'object' && !Array.isArray(authorsRaw)) {
    /** @type {Record<string, unknown>} */
    const authors = /** @type {Record<string, unknown>} */ (authorsRaw);
    const mode = authors.mode;
    if (mode === 'author-association' || mode === 'allow-list') {
      authorsMode = mode;
    }
    authorsAllowList = asStringList(authors['allow-list'] ?? authors.allowList);
    authorsAssociations = asStringList(
      authors['author-associations'] ?? authors.authorAssociations
    );
  }

  return {
    triggerLabels,
    forks: {
      mode: forksMode,
      authorAssociations: forksAssociations,
    },
    authors: {
      mode: authorsMode,
      allowList: authorsAllowList,
      authorAssociations: authorsAssociations,
    },
  };
}

/**
 * @param {string} rawJson
 * @returns {AutomergePolicy}
 */
function parseAutomergePolicyJson(rawJson) {
  if (!rawJson || typeof rawJson !== 'string' || !rawJson.trim()) {
    return defaultAutomergePolicy();
  }
  try {
    return normalizeAutomergePolicy(JSON.parse(rawJson));
  } catch {
    return defaultAutomergePolicy();
  }
}

/**
 * @param {AutomergePolicy} policy
 * @param {string[]} labelNames
 * @returns {boolean}
 */
function hasTriggerLabel(policy, labelNames) {
  const labels = new Set(labelNames);
  return policy.triggerLabels.some((name) => labels.has(name));
}

/**
 * Control-plane bots are always allowed. Repo allow-list and/or author
 * association gates apply on top depending on mode.
 * @param {AutomergePolicy} policy
 * @param {{ normalizedLogin: string, authorAssociation: string, isControlPlaneBot: boolean }} args
 * @returns {boolean}
 */
function isAuthorAllowedByPolicy(policy, args) {
  if (args.isControlPlaneBot) {
    return true;
  }
  if (policy.authors.mode === 'author-association') {
    const allowed = new Set(
      policy.authors.authorAssociations.map((item) => item.toUpperCase())
    );
    return allowed.has(String(args.authorAssociation || '').toUpperCase());
  }
  const extras = new Set(policy.authors.allowList);
  return extras.has(args.normalizedLogin);
}

/**
 * @param {AutomergePolicy} policy
 * @param {{ headFull: string, baseFull: string, authorAssociation: string }} args
 * @returns {boolean}
 */
function isForkAllowedByPolicy(policy, args) {
  if (args.headFull && args.baseFull && args.headFull === args.baseFull) {
    return true;
  }
  if (policy.forks.mode === 'disabled') {
    return false;
  }
  const allowed = new Set(
    policy.forks.authorAssociations.map((item) => item.toUpperCase())
  );
  return allowed.has(String(args.authorAssociation || '').toUpperCase());
}

module.exports = {
  MERGE_READY_LABEL,
  defaultAutomergePolicy,
  normalizeAutomergePolicy,
  parseAutomergePolicyJson,
  hasTriggerLabel,
  isAuthorAllowedByPolicy,
  isForkAllowedByPolicy,
};
