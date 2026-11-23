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
 * Validates the triggering pull request for automerge (author policy, trigger
 * labels, draft/fork/ref rules, and non-empty shared-token-policy when the author is
 * github-actions[bot] so approve can use Vault instead of self-APPROVE). Required status
 * checks are enforced by GitHub when auto-merge is enabled, not here.
 *
 * Control-plane bot logins live in `config/obs/allowed_pr_authors.json`, which Prelude
 * loads for ingress and `scripts/sync_allowed_pr_authors_bots.py` syncs onto static GH-AW
 * `on.bots` / prompt copies. Consumer `apm.yml` may extend authors, forks, and trigger
 * labels via `x-oblt-aw.<org>.workflows.automerge.policy` (see automergePolicy.ts).
 *
 * GraphQL/`gh pr view` (gh ≥ 2.50) may return `app/<slug>` for GitHub Apps while REST
 * and webhooks return `<slug>[bot]`. Matching always normalizes `app/<slug>` →
 * `<slug>[bot]` before comparing to the JSON allow list.
 *
 * ``automergePolicy.ts`` is optional at load time so released ``@v0`` callers that
 * sparse-checkout only this file keep working with control-plane defaults until their
 * workflow YAML is updated to fetch the sibling module.
 */
const path = require('node:path');
const fs = require('node:fs');

const MERGE_READY_LABEL_FALLBACK = 'oblt-aw/ai/merge-ready';

const DEFAULT_TRUSTED_LABEL_ACTOR_FALLBACK =
  'elastic-vault-github-plugin-prod[bot]';

function fallbackDefaultAutomergePolicy() {
  return {
    triggerLabels: [MERGE_READY_LABEL_FALLBACK],
    forks: { mode: 'disabled', authorAssociations: [] },
    authors: { mode: 'allow-list', allowList: [], authorAssociations: [] },
    paths: { allow: [], deny: [] },
    labelActors: { allow: [] },
  };
}

function loadAutomergePolicyModule() {
  try {
    // eslint-disable-next-line import/no-unresolved -- optional sibling for @v0 sparse checkouts
    return require('./automergePolicy.ts');
  } catch {
    return null;
  }
}

const policyModule = loadAutomergePolicyModule();
const MERGE_READY_LABEL =
  policyModule?.MERGE_READY_LABEL || MERGE_READY_LABEL_FALLBACK;
const DEFAULT_TRUSTED_LABEL_ACTOR =
  policyModule?.DEFAULT_TRUSTED_LABEL_ACTOR ||
  DEFAULT_TRUSTED_LABEL_ACTOR_FALLBACK;
const defaultAutomergePolicy =
  policyModule?.defaultAutomergePolicy || fallbackDefaultAutomergePolicy;
const normalizeAutomergePolicy =
  policyModule?.normalizeAutomergePolicy ||
  ((raw) => {
    if (!raw || typeof raw !== 'object') {
      return fallbackDefaultAutomergePolicy();
    }
    return fallbackDefaultAutomergePolicy();
  });
const parseAutomergePolicyJson =
  policyModule?.parseAutomergePolicyJson ||
  ((rawJson) => {
    if (!rawJson || typeof rawJson !== 'string' || !rawJson.trim()) {
      return fallbackDefaultAutomergePolicy();
    }
    try {
      return normalizeAutomergePolicy(JSON.parse(rawJson));
    } catch {
      return fallbackDefaultAutomergePolicy();
    }
  });
const hasTriggerLabel =
  policyModule?.hasTriggerLabel ||
  ((policy, labelNames) => {
    const labels = new Set(labelNames);
    return (policy.triggerLabels || [MERGE_READY_LABEL_FALLBACK]).some((name) =>
      labels.has(name)
    );
  });
const isLabelActorGateEnabled =
  policyModule?.isLabelActorGateEnabled ||
  ((policy) => (policy.labelActors?.allow || []).length > 0);
const hasTrustedTriggerLabel =
  policyModule?.hasTrustedTriggerLabel ||
  ((policy, presentLabelNames, latestAppliers) => {
    if (!hasTriggerLabel(policy, presentLabelNames)) {
      return false;
    }
    if (!isLabelActorGateEnabled(policy)) {
      return true;
    }
    const present = new Set(presentLabelNames);
    const allow = new Set(policy.labelActors?.allow || []);
    return (policy.triggerLabels || []).some((name) => {
      if (!present.has(name)) {
        return false;
      }
      const actor =
        latestAppliers instanceof Map
          ? latestAppliers.get(name)
          : latestAppliers[name];
      if (actor == null || actor === '') {
        return false;
      }
      const normalized = normalizePrAuthorLogin(actor);
      return allow.has(normalized);
    });
  });
const isAuthorAllowedByPolicy =
  policyModule?.isAuthorAllowedByPolicy ||
  ((policy, args) => {
    if (args.isControlPlaneBot) {
      return true;
    }
    if (policy.authors?.mode === 'author-association') {
      const allowed = new Set(
        (policy.authors.authorAssociations || []).map((item) =>
          String(item).toUpperCase()
        )
      );
      return allowed.has(String(args.authorAssociation || '').toUpperCase());
    }
    return new Set(policy.authors?.allowList || []).has(args.normalizedLogin);
  });
const isForkAllowedByPolicy =
  policyModule?.isForkAllowedByPolicy ||
  ((policy, args) => {
    if (args.headFull && args.baseFull && args.headFull === args.baseFull) {
      return true;
    }
    if ((policy.forks?.mode || 'disabled') === 'disabled') {
      return false;
    }
    const allowed = new Set(
      (policy.forks?.authorAssociations || []).map((item) =>
        String(item).toUpperCase()
      )
    );
    return allowed.has(String(args.authorAssociation || '').toUpperCase());
  });

const GITHUB_ACTIONS_BOT = 'github-actions[bot]';

const ALLOWED_PR_AUTHORS = new Set(
  JSON.parse(
    fs.readFileSync(
      path.join(__dirname, '..', '..', 'config', 'obs', 'allowed_pr_authors.json'),
      'utf8'
    )
  )
);

/**
 * Map GraphQL app actor logins to the REST/`…[bot]` form used in allowed_pr_authors.json.
 * Leave other logins unchanged (including human Dependabot/Renovate display names).
 */
function normalizePrAuthorLogin(login) {
  const raw = String(login || '').trim();
  if (!raw) {
    return '';
  }
  const appMatch = /^app\/([^/]+)$/i.exec(raw);
  if (appMatch) {
    return `${appMatch[1]}[bot]`;
  }
  return raw;
}

function isAllowedPrAuthor(login) {
  return ALLOWED_PR_AUTHORS.has(normalizePrAuthorLogin(login));
}

module.exports.normalizePrAuthorLogin = normalizePrAuthorLogin;
module.exports.isAllowedPrAuthor = isAllowedPrAuthor;
module.exports.MERGE_READY_LABEL = MERGE_READY_LABEL;
module.exports.DEFAULT_TRUSTED_LABEL_ACTOR = DEFAULT_TRUSTED_LABEL_ACTOR;
module.exports.defaultAutomergePolicy = defaultAutomergePolicy;
module.exports.normalizeAutomergePolicy = normalizeAutomergePolicy;

/**
 * Latest labeled/unlabeled applier per label name from the issue timeline.
 * Fail-closed callers must treat thrown errors as gate failure.
 * @param {{ paginate: Function, rest: { issues: { listEventsForTimeline: unknown } } }} github
 * @param {{ owner: string, repo: string, issueNumber: number }} args
 * @returns {Promise<Map<string, string|null>>}
 */
async function resolveLatestLabelAppliers(github, args) {
  const events = await github.paginate(github.rest.issues.listEventsForTimeline, {
    owner: args.owner,
    repo: args.repo,
    issue_number: args.issueNumber,
    per_page: 100,
  });
  /** @type {Map<string, string|null>} */
  const latest = new Map();
  for (const event of events || []) {
    if (event?.event !== 'labeled' && event?.event !== 'unlabeled') {
      continue;
    }
    const name = event.label?.name;
    if (typeof name !== 'string' || !name) {
      continue;
    }
    if (event.event === 'unlabeled') {
      latest.set(name, null);
      continue;
    }
    latest.set(name, normalizePrAuthorLogin(event.actor?.login || ''));
  }
  return latest;
}

module.exports.resolveLatestLabelAppliers = resolveLatestLabelAppliers;

module.exports.run = async function run({
  github,
  context,
  prNumber,
  core,
  sharedTokenPolicy = '',
  policy = undefined,
  policyJson = '',
}) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  if (typeof prNumber !== 'number' || !Number.isFinite(prNumber)) {
    core.info('Automerge: invalid or missing pull request number; skipping.');
    return { ok: false, triggerLabels: [], labelActorsAllow: [] };
  }

  let effectivePolicy;
  try {
    effectivePolicy =
      policy && typeof policy === 'object'
        ? normalizeAutomergePolicy(policy)
        : parseAutomergePolicyJson(policyJson);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    core.info(
      `PR #${prNumber}: invalid automerge policy (${message}); skipping.`
    );
    return { ok: false, triggerLabels: [], labelActorsAllow: [] };
  }
  const labelActorsAllow = effectivePolicy.labelActors?.allow || [];

  const { data: pr } = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: prNumber,
  });

  const authorRaw = pr.user?.login || '';
  const author = normalizePrAuthorLogin(authorRaw);
  const authorAssociation = String(pr.author_association || '');
  const isControlPlaneBot = ALLOWED_PR_AUTHORS.has(author);

  if (
    !isAuthorAllowedByPolicy(effectivePolicy, {
      normalizedLogin: author,
      authorAssociation,
      isControlPlaneBot,
    })
  ) {
    core.info(
      `PR #${prNumber}: author '${authorRaw}'` +
        (author !== authorRaw ? ` (normalized '${author}')` : '') +
        ` association='${authorAssociation}' is not allowed by automerge policy`
    );
    return {
      ok: false,
      triggerLabels: effectivePolicy.triggerLabels,
      labelActorsAllow,
    };
  }

  // Approve must use Vault for github-actions-authored PRs (GITHUB_TOKEN would self-APPROVE).
  if (author === GITHUB_ACTIONS_BOT && !(sharedTokenPolicy || '').trim()) {
    core.info(
      `PR #${prNumber}: author '${GITHUB_ACTIONS_BOT}' requires a non-empty shared-token-policy so approve can use Vault instead of GITHUB_TOKEN`
    );
    return {
      ok: false,
      triggerLabels: effectivePolicy.triggerLabels,
      labelActorsAllow,
    };
  }

  const labelNames = (pr.labels || []).map((l) => l.name);
  if (!hasTriggerLabel(effectivePolicy, labelNames)) {
    core.info(
      `PR #${prNumber}: missing trigger label (need one of: ${effectivePolicy.triggerLabels.join(', ')})`
    );
    return {
      ok: false,
      triggerLabels: effectivePolicy.triggerLabels,
      labelActorsAllow,
    };
  }

  if (isLabelActorGateEnabled(effectivePolicy)) {
    let latestAppliers;
    try {
      latestAppliers = await resolveLatestLabelAppliers(github, {
        owner,
        repo,
        issueNumber: prNumber,
      });
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      core.info(
        `PR #${prNumber}: could not read label timeline (fail closed): ${message}`
      );
      return {
        ok: false,
        triggerLabels: effectivePolicy.triggerLabels,
        labelActorsAllow,
      };
    }
    if (!hasTrustedTriggerLabel(effectivePolicy, labelNames, latestAppliers)) {
      core.info(
        `PR #${prNumber}: no trigger label applied by an allowed actor ` +
          `(allow: ${labelActorsAllow.join(', ')})`
      );
      return {
        ok: false,
        triggerLabels: effectivePolicy.triggerLabels,
        labelActorsAllow,
      };
    }
  }

  if (pr.draft) {
    core.info(`PR #${prNumber}: draft PRs are excluded`);
    return {
      ok: false,
      triggerLabels: effectivePolicy.triggerLabels,
      labelActorsAllow,
    };
  }

  const headFull = pr.head?.repo?.full_name || '';
  const baseFull = pr.base?.repo?.full_name || '';
  if (
    !isForkAllowedByPolicy(effectivePolicy, {
      headFull,
      baseFull,
      authorAssociation,
    })
  ) {
    core.info(
      `PR #${prNumber}: fork PRs are excluded by automerge policy (forks.mode=${effectivePolicy.forks.mode})`
    );
    return {
      ok: false,
      triggerLabels: effectivePolicy.triggerLabels,
      labelActorsAllow,
    };
  }

  if ((pr.head?.ref || '') === (pr.base?.ref || '')) {
    core.info(`PR #${prNumber}: head ref equals base ref`);
    return {
      ok: false,
      triggerLabels: effectivePolicy.triggerLabels,
      labelActorsAllow,
    };
  }

  core.info(`PR #${prNumber}: passed automerge validation`);
  return {
    ok: true,
    triggerLabels: effectivePolicy.triggerLabels,
    labelActorsAllow,
  };
};
