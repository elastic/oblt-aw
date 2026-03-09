// @ts-nocheck
const test = require('node:test');
const assert = require('node:assert/strict');

const { run } = require('../../scripts/findAutomergeCandidates.ts');

test('findAutomergeCandidates returns sorted unique qualifying PR numbers', async () => {
  const mockGithub = {
    rest: {
      pulls: {
        list: Symbol('list'),
      },
    },
    paginate: async (listMethod, params) => {
      assert.equal(listMethod, mockGithub.rest.pulls.list);
      assert.deepEqual(params, {
        owner: 'elastic',
        repo: 'automerge',
        state: 'open',
        per_page: 100,
      });

      return [
        {
          number: 10,
          user: { login: 'elastic-vault-github-plugin-prod[bot]' },
          labels: [{ name: 'oblt-aw/ai/merge-ready' }],
          draft: false,
          head: { repo: { full_name: 'elastic/automerge' }, ref: 'feature/a' },
          base: { repo: { full_name: 'elastic/automerge' }, ref: 'main' },
        },
        {
          number: 2,
          user: { login: 'elastic-vault-github-plugin-prod[bot]' },
          labels: [{ name: 'oblt-aw/ai/merge-ready' }],
          draft: false,
          head: { repo: { full_name: 'elastic/automerge' }, ref: 'feature/b' },
          base: { repo: { full_name: 'elastic/automerge' }, ref: 'main' },
        },
        {
          number: 10,
          user: { login: 'elastic-vault-github-plugin-prod[bot]' },
          labels: [{ name: 'oblt-aw/ai/merge-ready' }],
          draft: false,
          head: { repo: { full_name: 'elastic/automerge' }, ref: 'feature/a' },
          base: { repo: { full_name: 'elastic/automerge' }, ref: 'main' },
        },
      ];
    },
  };

  const result = await run({
    github: mockGithub,
    context: { repo: { owner: 'elastic', repo: 'automerge' } },
    mergeReadyLabel: 'oblt-aw/ai/merge-ready',
    allowedActor: 'elastic-vault-github-plugin-prod[bot]',
  });

  assert.deepEqual(result, { prNumbers: [2, 10] });
});

test('findAutomergeCandidates filters out non-qualifying PRs', async () => {
  const mockGithub = {
    rest: {
      pulls: {
        list: Symbol('list'),
      },
    },
    paginate: async () => [
      {
        number: 1,
        user: { login: 'someone-else' },
        labels: [{ name: 'oblt-aw/ai/merge-ready' }],
        draft: false,
        head: { repo: { full_name: 'elastic/automerge' }, ref: 'branch-1' },
        base: { repo: { full_name: 'elastic/automerge' }, ref: 'main' },
      },
      {
        number: 2,
        user: { login: 'elastic-vault-github-plugin-prod[bot]' },
        labels: [{ name: 'other-label' }],
        draft: false,
        head: { repo: { full_name: 'elastic/automerge' }, ref: 'branch-2' },
        base: { repo: { full_name: 'elastic/automerge' }, ref: 'main' },
      },
      {
        number: 3,
        user: { login: 'elastic-vault-github-plugin-prod[bot]' },
        labels: [{ name: 'oblt-aw/ai/merge-ready' }],
        draft: true,
        head: { repo: { full_name: 'elastic/automerge' }, ref: 'branch-3' },
        base: { repo: { full_name: 'elastic/automerge' }, ref: 'main' },
      },
      {
        number: 4,
        user: { login: 'elastic-vault-github-plugin-prod[bot]' },
        labels: [{ name: 'oblt-aw/ai/merge-ready' }],
        draft: false,
        head: { repo: { full_name: 'fork/automerge' }, ref: 'branch-4' },
        base: { repo: { full_name: 'elastic/automerge' }, ref: 'main' },
      },
      {
        number: 5,
        user: { login: 'elastic-vault-github-plugin-prod[bot]' },
        labels: [{ name: 'oblt-aw/ai/merge-ready' }],
        draft: false,
        head: { repo: { full_name: 'elastic/automerge' }, ref: 'main' },
        base: { repo: { full_name: 'elastic/automerge' }, ref: 'main' },
      },
    ],
  };

  const result = await run({
    github: mockGithub,
    context: { repo: { owner: 'elastic', repo: 'automerge' } },
    mergeReadyLabel: 'oblt-aw/ai/merge-ready',
    allowedActor: 'elastic-vault-github-plugin-prod[bot]',
  });

  assert.deepEqual(result, { prNumbers: [] });
});
