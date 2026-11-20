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
 * allow-list (control-plane bots only unless the repo adds names), and no
 * path restriction for ``all-files`` (empty allow/deny means unrestricted), and
 * no weekday restriction (empty ``allowedDaysOfWeek`` means all UTC days).
 *
 * Path globs support only ``*`` and ``**`` (same as collection file-glob).
 */

const MERGE_READY_LABEL = 'oblt-aw/ai/merge-ready';

/** Top-level policy keys (kebab + camel) accepted by normalize. */
const KNOWN_POLICY_KEYS = new Set([
  'allowed-days-of-week',
  'allowedDaysOfWeek',
  'authors',
  'forks',
  'paths',
  'trigger-labels',
  'triggerLabels',
]);

const KNOWN_PATH_KEYS = new Set(['allow', 'deny']);

/** Unsupported in path globs (matcher only implements ``*`` / ``**``). */
const UNSUPPORTED_GLOB_CHARS = /[?[\]]/;

/** UTC weekday names indexed by ``Date#getUTCDay()`` (0 = Sunday). */
const UTC_WEEKDAY_NAMES = [
  'sunday',
  'monday',
  'tuesday',
  'wednesday',
  'thursday',
  'friday',
  'saturday',
];

const ALLOWED_WEEKDAY_SET = new Set(UTC_WEEKDAY_NAMES);

/** @typedef {'disabled' | 'author-association'} ForksMode */
/** @typedef {'allow-list' | 'author-association'} AuthorsMode */

/** @typedef {object} AutomergePathPolicy
 * @property {string[]} allow Empty means every path is allowed (deny still applies).
 * @property {string[]} deny Empty means nothing is denied. Deny wins over allow.
 */

/** @typedef {object} AutomergePolicy
 * @property {string[]} triggerLabels
 * @property {{ mode: ForksMode, authorAssociations: string[] }} forks
 * @property {{ mode: AuthorsMode, allowList: string[], authorAssociations: string[] }} authors
 * @property {string[]} allowedDaysOfWeek Empty means unrestricted (all UTC weekdays).
 * @property {AutomergePathPolicy} paths Applies only to the ``all-files`` collection.
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
    paths: {
      allow: [],
      deny: [],
    },
    allowedDaysOfWeek: [],
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
 * @param {string} pattern
 * @param {string} fieldName
 */
function assertSupportedPathGlob(pattern, fieldName) {
  if (UNSUPPORTED_GLOB_CHARS.test(pattern)) {
    throw new Error(
      `paths.${fieldName} pattern '${pattern}' uses unsupported glob syntax ` +
        '(only * and ** are supported)'
    );
  }
}

/**
 * Normalize path glob lists. Omitted / empty ⇒ unrestricted for that list.
 * Present but non-array, blank entries, unsupported syntax, or non-strings
 * fail closed.
 * @param {unknown} value
 * @param {string} fieldName
 * @param {boolean} present
 * @returns {string[]}
 */
function asPathGlobList(value, fieldName, present) {
  if (!present) {
    return [];
  }
  if (!Array.isArray(value)) {
    throw new Error(
      `paths.${fieldName} must be an array of glob strings, or omitted / []`
    );
  }
  /** @type {string[]} */
  const out = [];
  const seen = new Set();
  for (const item of value) {
    if (typeof item !== 'string') {
      throw new Error(
        `paths.${fieldName} entries must be strings; got ${typeof item}`
      );
    }
    if (item !== item.trim()) {
      throw new Error(
        `paths.${fieldName} entries must not have leading or trailing whitespace`
      );
    }
    if (!item) {
      throw new Error(
        `paths.${fieldName} entries must be non-empty glob strings`
      );
    }
    assertSupportedPathGlob(item, fieldName);
    if (seen.has(item)) {
      continue;
    }
    seen.add(item);
    out.push(item);
  }
  return out;
}

/**
 * Normalize weekday allow-list. Omitted / empty ⇒ unrestricted.
 * Any non-array value, or any entry that is not a known weekday name, fails closed.
 * @param {unknown} value
 * @param {boolean} present
 * @returns {string[]}
 */
function asAllowedDaysOfWeek(value, present) {
  if (!present) {
    return [];
  }
  if (!Array.isArray(value)) {
    throw new Error(
      'allowed-days-of-week must be an array of weekday names (monday … sunday), or omitted / [] for all days'
    );
  }
  if (value.length === 0) {
    return [];
  }
  const seen = new Set();
  /** @type {string[]} */
  const out = [];
  for (const item of value) {
    if (typeof item !== 'string') {
      throw new Error(
        `allowed-days-of-week entries must be strings; got ${typeof item}`
      );
    }
    const day = item.trim().toLowerCase();
    if (!ALLOWED_WEEKDAY_SET.has(day)) {
      throw new Error(
        `allowed-days-of-week contains unknown weekday '${item.trim()}'; (expected monday … sunday)`
      );
    }
    if (seen.has(day)) {
      continue;
    }
    seen.add(day);
    out.push(day);
  }
  return out;
}

/**
 * @param {unknown} raw
 * @param {boolean} present
 * @returns {AutomergePathPolicy}
 */
function asPathPolicy(raw, present) {
  if (!present) {
    return { allow: [], deny: [] };
  }
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) {
    throw new Error(
      'paths must be a mapping with optional allow/deny glob arrays'
    );
  }
  /** @type {Record<string, unknown>} */
  const obj = /** @type {Record<string, unknown>} */ (raw);
  const unknown = Object.keys(obj)
    .filter((key) => !KNOWN_PATH_KEYS.has(key))
    .sort((a, b) => a.localeCompare(b));
  if (unknown.length > 0) {
    throw new Error(
      `paths contains unknown key(s): ${unknown.join(', ')} (expected allow, deny)`
    );
  }
  const allowPresent = Object.prototype.hasOwnProperty.call(obj, 'allow');
  const denyPresent = Object.prototype.hasOwnProperty.call(obj, 'deny');
  return {
    allow: asPathGlobList(obj.allow, 'allow', allowPresent),
    deny: asPathGlobList(obj.deny, 'deny', denyPresent),
  };
}

/**
 * @param {Record<string, unknown>} obj
 * @returns {string[]}
 */
function unknownPolicyKeys(obj) {
  return Object.keys(obj)
    .filter((key) => !KNOWN_POLICY_KEYS.has(key))
    .sort((a, b) => a.localeCompare(b));
}

/**
 * Normalize a raw policy mapping (kebab-case from apm.yml or camelCase JSON).
 * Always includes ``oblt-aw/ai/merge-ready`` in trigger labels.
 * Invalid ``paths`` values throw (callers must fail closed).
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

  const unknown = unknownPolicyKeys(obj);
  if (unknown.length > 0) {
    console.warn(
      `automerge policy: ignoring unknown key(s): ${unknown.join(', ')}`
    );
  }

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

  const pathsPresent = Object.prototype.hasOwnProperty.call(obj, 'paths');
  const paths = asPathPolicy(obj.paths, pathsPresent);

  const daysPresent =
    Object.prototype.hasOwnProperty.call(obj, 'allowed-days-of-week') ||
    Object.prototype.hasOwnProperty.call(obj, 'allowedDaysOfWeek');
  const allowedDaysOfWeek = asAllowedDaysOfWeek(
    obj['allowed-days-of-week'] ?? obj.allowedDaysOfWeek,
    daysPresent
  );

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
    paths,
    allowedDaysOfWeek,
  };
}

/**
 * Parse policy JSON. Empty input ⇒ defaults. Invalid JSON or invalid
 * ``paths`` values throw (callers must fail closed).
 * @param {string} rawJson
 * @returns {AutomergePolicy}
 */
/**
 * Parse policy JSON. Empty input ⇒ defaults. Invalid JSON or invalid
 * ``allowed-days-of-week`` values throw (callers must fail closed).
 * @param {string} rawJson
 * @returns {AutomergePolicy}
 */
function parseAutomergePolicyJson(rawJson) {
  if (!rawJson || typeof rawJson !== 'string' || !rawJson.trim()) {
    return defaultAutomergePolicy();
  }
  return normalizeAutomergePolicy(JSON.parse(rawJson));
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

/** JS line terminators that can split a path segment and bypass globs. */
const PATH_LINE_TERMINATORS = /[\n\r\u2028\u2029]/;

/**
 * GitHub paths are forward-slash and unpadded. Reject ambiguous names when
 * path restrictions are active so trim/`\`/newline rewrites cannot widen matches.
 * @param {string} filePath
 * @returns {boolean}
 */
function isSafeRepoPathForPolicy(filePath) {
  if (typeof filePath !== 'string' || !filePath) {
    return false;
  }
  if (filePath !== filePath.trim()) {
    return false;
  }
  if (filePath.includes('\\')) {
    return false;
  }
  if (PATH_LINE_TERMINATORS.test(filePath)) {
    return false;
  }
  return true;
}

/**
 * Whether every path is eligible under ``all-files`` path policy.
 * Empty allow ⇒ all paths allowed; empty deny ⇒ nothing denied; deny wins.
 * Loads the glob matcher lazily so verify callers that only need labels/authors
 * do not require ``lib/matchPathGlob.ts`` in sparse checkout.
 * @param {string[]} files
 * @param {AutomergePathPolicy} [paths]
 * @returns {boolean}
 */
function filesMatchAllFilesPathPolicy(files, paths) {
  const changed = [...new Set(files.filter((f) => typeof f === 'string' && f))];
  if (changed.length === 0) {
    return false;
  }
  const allow = paths?.allow || [];
  const deny = paths?.deny || [];
  const restricted = allow.length > 0 || deny.length > 0;
  if (restricted && changed.some((file) => !isSafeRepoPathForPolicy(file))) {
    return false;
  }
  if (!restricted) {
    return true;
  }
  // Lazy require: verify sparse checkout may omit the matcher until path checks run.
  const { pathMatchesAnyGlob } = require('./lib/matchPathGlob.ts');
  return changed.every((file) => {
    if (deny.length > 0 && pathMatchesAnyGlob(file, deny)) {
      return false;
    }
    if (allow.length > 0 && !pathMatchesAnyGlob(file, allow)) {
      return false;
    }
    return true;
  });
}

/**
 * Empty ``allowedDaysOfWeek`` means unrestricted. Otherwise the UTC weekday
 * of ``when`` must be listed (lowercase English names).
 * @param {AutomergePolicy} policy
 * @param {Date} [when]
 * @returns {boolean}
 */
function isDayAllowedByPolicy(policy, when = new Date()) {
  const allowed = policy.allowedDaysOfWeek || [];
  if (!allowed.length) {
    return true;
  }
  const day = UTC_WEEKDAY_NAMES[when.getUTCDay()];
  return allowed.includes(day);
}

/**
 * @param {Date} [when]
 * @returns {string}
 */
function utcWeekdayName(when = new Date()) {
  return UTC_WEEKDAY_NAMES[when.getUTCDay()];
}

module.exports = {
  MERGE_READY_LABEL,
  KNOWN_POLICY_KEYS,
  UTC_WEEKDAY_NAMES,
  defaultAutomergePolicy,
  normalizeAutomergePolicy,
  parseAutomergePolicyJson,
  hasTriggerLabel,
  isAuthorAllowedByPolicy,
  isForkAllowedByPolicy,
  filesMatchAllFilesPathPolicy,
  isSafeRepoPathForPolicy,
  isDayAllowedByPolicy,
  utcWeekdayName,
};
