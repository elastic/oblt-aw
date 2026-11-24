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

// @ts-nocheck
const test = require('node:test');
const assert = require('node:assert/strict');

const {
  run,
  normalizePrAuthorLogin,
  isAllowedPrAuthor,
} = require('../../scripts/obs/validateAutomergePr.ts');

function makeCore() {
  const infoMessages = [];
  return {
    core: { info: (msg) => infoMessages.push(msg) },
    infoMessages,
  };
}

function basePr(overrides = {}) {
  return {
    user: { login: 'dependabot[bot]' },
    labels: [{ name: 'oblt-aw/ai/merge-ready' }],
    draft: false,
    head: { sha: 'abc', repo: { full_name: 'elastic/r' }, ref: 'feat' },
    base: { repo: { full_name: 'elastic/r' }, ref: 'main' },
    ...overrides,
  };
}

test('normalizePrAuthorLogin maps GraphQL app/ to REST bot login', () => {
  assert.equal(normalizePrAuthorLogin('app/dependabot'), 'dependabot[bot]');
  assert.equal(
    normalizePrAuthorLogin('app/elastic-renovate-prod'),
    'elastic-renovate-prod[bot]'
  );
  assert.equal(
    normalizePrAuthorLogin('app/elastic-vault-github-plugin-prod'),
    'elastic-vault-github-plugin-prod[bot]'
  );
  assert.equal(normalizePrAuthorLogin('app/github-actions'), 'github-actions[bot]');
  assert.equal(normalizePrAuthorLogin('dependabot[bot]'), 'dependabot[bot]');
  assert.equal(normalizePrAuthorLogin('Dependabot'), 'Dependabot');
  assert.equal(normalizePrAuthorLogin(''), '');
});

test('isAllowedPrAuthor uses allowed_pr_authors.json after normalize', () => {
  assert.equal(isAllowedPrAuthor('dependabot[bot]'), true);
  assert.equal(isAllowedPrAuthor('app/dependabot'), true);
  assert.equal(isAllowedPrAuthor('app/renovate'), true);
  assert.equal(isAllowedPrAuthor('elastic-renovate-prod[bot]'), true);
  assert.equal(isAllowedPrAuthor('app/elastic-renovate-prod'), true);
  assert.equal(isAllowedPrAuthor('app/other-bot'), false);
  assert.equal(isAllowedPrAuthor('human'), false);
});

test('validateAutomergePr returns not ok for invalid pr number', async () => {
  const { core } = makeCore();
  const r = await run({
    github: {},
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: NaN,
    core,
  });
  assert.equal(r.ok, false);
});

test('validateAutomergePr returns not ok when author not allowed', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: basePr({ user: { login: 'human' } }) }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 1,
    core,
  });
  assert.equal(r.ok, false);
});

test('validateAutomergePr returns not ok without merge-ready label', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: basePr({ labels: [{ name: 'other' }] }) }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 1,
    core,
  });
  assert.equal(r.ok, false);
});

test('validateAutomergePr returns not ok for draft, fork, or same ref', async () => {
  const { core } = makeCore();
  for (const data of [
    basePr({ draft: true }),
    basePr({ head: { sha: 'a', repo: { full_name: 'fork/r' }, ref: 'f' } }),
    basePr({ head: { sha: 'a', repo: { full_name: 'elastic/r' }, ref: 'main' }, base: { repo: { full_name: 'elastic/r' }, ref: 'main' } }),
  ]) {
    const github = {
      rest: {
        pulls: { get: async () => ({ data }) },
      },
    };
    const r = await run({
      github,
      context: { repo: { owner: 'elastic', repo: 'r' } },
      prNumber: 9,
      core,
    });
    assert.equal(r.ok, false);
  }
});

test('validateAutomergePr returns ok when all gates pass', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: { get: async () => ({ data: basePr() }) },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 42,
    core,
  });
  assert.equal(r.ok, true);
});

test('validateAutomergePr allows GraphQL app/dependabot via normalize', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: basePr({ user: { login: 'app/dependabot' } }) }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 1115,
    core,
  });
  assert.equal(r.ok, true);
});

test('validateAutomergePr allows elastic-renovate-prod[bot]', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: basePr({ user: { login: 'elastic-renovate-prod[bot]' } }) }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 6,
    core,
  });
  assert.equal(r.ok, true);
});

test('validateAutomergePr allows elastic-vault-github-plugin-prod[bot]', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: basePr({ user: { login: 'elastic-vault-github-plugin-prod[bot]' } }) }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 7,
    core,
  });
  assert.equal(r.ok, true);
});

test('validateAutomergePr allows github-actions[bot] when shared-token-policy is set', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: basePr({ user: { login: 'github-actions[bot]' } }) }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 8,
    core,
    sharedTokenPolicy: 'token-policy-example',
  });
  assert.equal(r.ok, true);
});

test('validateAutomergePr rejects github-actions[bot] when shared-token-policy is empty', async () => {
  const { core, infoMessages } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: basePr({ user: { login: 'github-actions[bot]' } }) }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 8,
    core,
    sharedTokenPolicy: '',
  });
  assert.equal(r.ok, false);
  assert.match(infoMessages.join('\n'), /shared-token-policy/);
});

test('validateAutomergePr allows custom trigger label from policy', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({
          data: basePr({
            labels: [{ name: 'nightshift:risk-low' }],
          }),
        }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 20,
    core,
    policy: {
      'trigger-labels': ['nightshift:risk-low'],
    },
  });
  assert.equal(r.ok, true);
});

test('validateAutomergePr accepts trusted label actor from timeline', async () => {
  const { core } = makeCore();
  const github = {
    paginate: async () => [
      {
        event: 'labeled',
        label: { name: 'nightshift:risk-low' },
        actor: { login: 'nightshift-bot[bot]' },
      },
    ],
    rest: {
      pulls: {
        get: async () => ({
          data: basePr({
            labels: [{ name: 'nightshift:risk-low' }],
          }),
        }),
      },
      issues: { listEventsForTimeline: {} },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 30,
    core,
    policy: {
      'trigger-labels': ['nightshift:risk-low'],
      'label-actors': { allow: ['nightshift-bot[bot]'] },
    },
  });
  assert.equal(r.ok, true);
  assert.ok(r.labelActorsAllow.includes('elastic-vault-github-plugin-prod[bot]'));
});

test('validateAutomergePr rejects untrusted label actor', async () => {
  const { core, infoMessages } = makeCore();
  const github = {
    paginate: async () => [
      {
        event: 'labeled',
        label: { name: 'oblt-aw/ai/merge-ready' },
        actor: { login: 'random-triager' },
      },
    ],
    rest: {
      pulls: {
        get: async () => ({ data: basePr() }),
      },
      issues: { listEventsForTimeline: {} },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 31,
    core,
    policy: {
      'label-actors': { allow: [] },
    },
  });
  assert.equal(r.ok, false);
  assert.match(infoMessages.join('\n'), /allowed actor/);
});

test('validateAutomergePr fails closed when timeline cannot be read', async () => {
  const { core, infoMessages } = makeCore();
  const github = {
    paginate: async () => {
      throw new Error('timeline boom');
    },
    rest: {
      pulls: {
        get: async () => ({ data: basePr() }),
      },
      issues: { listEventsForTimeline: {} },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 32,
    core,
    policy: {
      'label-actors': { allow: ['nightshift-bot[bot]'] },
    },
  });
  assert.equal(r.ok, false);
  assert.match(infoMessages.join('\n'), /timeline/);
});

test('validateAutomergePr rejects when latest reapply is untrusted after trusted history', async () => {
  const { core, infoMessages } = makeCore();
  const label = 'oblt-aw/ai/merge-ready';
  const github = {
    paginate: async () => [
      {
        event: 'labeled',
        label: { name: label },
        actor: { login: 'nightshift-bot[bot]' },
      },
      {
        event: 'unlabeled',
        label: { name: label },
        actor: { login: 'nightshift-bot[bot]' },
      },
      {
        event: 'labeled',
        label: { name: label },
        actor: { login: 'random-triager' },
      },
    ],
    rest: {
      pulls: {
        get: async () => ({ data: basePr() }),
      },
      issues: { listEventsForTimeline: {} },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 33,
    core,
    policy: {
      'label-actors': { allow: ['nightshift-bot[bot]'] },
    },
  });
  assert.equal(r.ok, false);
  assert.match(infoMessages.join('\n'), /allowed actor/);
});

test('validateAutomergePr accepts when latest reapply is trusted after untrusted history', async () => {
  const { core } = makeCore();
  const label = 'oblt-aw/ai/merge-ready';
  const github = {
    // Simulate octokit.paginate flattening two timeline pages.
    paginate: async () => [
      {
        event: 'labeled',
        label: { name: label },
        actor: { login: 'random-triager' },
      },
      {
        event: 'unlabeled',
        label: { name: label },
        actor: { login: 'random-triager' },
      },
      {
        event: 'labeled',
        label: { name: label },
        actor: { login: 'nightshift-bot[bot]' },
      },
    ],
    rest: {
      pulls: {
        get: async () => ({ data: basePr() }),
      },
      issues: { listEventsForTimeline: {} },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 34,
    core,
    policy: {
      'label-actors': { allow: ['nightshift-bot[bot]'] },
    },
  });
  assert.equal(r.ok, true);
});

test('validateAutomergePr allows MEMBER fork when forks.mode is author-association', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({
          data: basePr({
            author_association: 'MEMBER',
            head: { sha: 'a', repo: { full_name: 'alice/r' }, ref: 'feat' },
            base: { repo: { full_name: 'elastic/r' }, ref: 'main' },
          }),
        }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 21,
    core,
    policy: {
      forks: {
        mode: 'author-association',
        'author-associations': ['MEMBER', 'OWNER'],
      },
    },
  });
  assert.equal(r.ok, true);
});

test('validateAutomergePr allows MEMBER author when authors.mode is author-association', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({
          data: basePr({
            user: { login: 'elastic-engineer' },
            author_association: 'MEMBER',
          }),
        }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 22,
    core,
    policy: {
      authors: {
        mode: 'author-association',
        'author-associations': ['MEMBER', 'OWNER'],
      },
    },
  });
  assert.equal(r.ok, true);
});

test('validateAutomergePr still rejects untrusted fork under author-association policy', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        get: async () => ({
          data: basePr({
            author_association: 'NONE',
            head: { sha: 'a', repo: { full_name: 'outsider/r' }, ref: 'feat' },
            base: { repo: { full_name: 'elastic/r' }, ref: 'main' },
          }),
        }),
      },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 23,
    core,
    policy: {
      forks: {
        mode: 'author-association',
        'author-associations': ['MEMBER', 'OWNER'],
      },
    },
  });
  assert.equal(r.ok, false);
});

test('validateAutomergePr soft-defers disallowed UTC weekday (ok true, weekdayOk false)', async () => {
  const { core, infoMessages } = makeCore();
  const github = {
    rest: {
      pulls: { get: async () => ({ data: basePr() }) },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 77,
    core,
    policy: {
      'allowed-days-of-week': ['monday', 'tuesday', 'wednesday', 'thursday'],
    },
    now: new Date('2026-11-20T12:00:00Z'), // Friday UTC
  });
  assert.equal(r.ok, true);
  assert.equal(r.weekdayOk, false);
  assert.deepEqual(r.allowedDaysOfWeek, [
    'monday',
    'tuesday',
    'wednesday',
    'thursday',
  ]);
  assert.ok(
    infoMessages.some((msg) => msg.includes("UTC weekday 'friday'")),
    infoMessages.join('\n')
  );
});

test('validateAutomergePr allows listed UTC weekday', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: { get: async () => ({ data: basePr() }) },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 78,
    core,
    policy: {
      'allowed-days-of-week': ['monday', 'tuesday', 'wednesday', 'thursday'],
    },
    now: new Date('2026-11-16T12:00:00Z'), // Monday UTC
  });
  assert.equal(r.ok, true);
  assert.equal(r.weekdayOk, true);
});

test('validateAutomergePr treats empty allowed-days-of-week as unrestricted', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: { get: async () => ({ data: basePr() }) },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 79,
    core,
    policy: { 'allowed-days-of-week': [] },
    now: new Date('2026-11-20T12:00:00Z'), // Friday UTC
  });
  assert.equal(r.ok, true);
  assert.equal(r.weekdayOk, true);
});

test('validateAutomergePr fails closed on malformed allowed-days-of-week', async () => {
  const { core, infoMessages } = makeCore();
  const github = {
    rest: {
      pulls: { get: async () => ({ data: basePr() }) },
    },
  };
  const r = await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' } },
    prNumber: 80,
    core,
    policy: { 'allowed-days-of-week': ['monady'] },
  });
  assert.equal(r.ok, false);
  assert.equal(r.weekdayOk, false);
  assert.ok(
    infoMessages.some((msg) => msg.includes('invalid consumer policy')),
    infoMessages.join('\n')
  );
});
