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

const { run } = require('../../scripts/enableAutomergeForApprovedPr.ts');

function makeCore() {
  const infoMessages = [];
  const warnings = [];
  return {
    core: {
      info: (msg) => infoMessages.push(msg),
      warning: (msg) => warnings.push(msg),
    },
    infoMessages,
    warnings,
  };
}

test('enableAutomergeForApprovedPr exits when pr number invalid', async () => {
  const { core, infoMessages } = makeCore();

  await run({
    github: {},
    context: { repo: { owner: 'elastic', repo: 'automerge' } },
    core,
    prNumber: NaN,
  });

  assert.equal(infoMessages[0], 'No pull request number for auto-merge enablement.');
});

test('enableAutomergeForApprovedPr enables auto-merge when approval exists', async () => {
  const { core, infoMessages } = makeCore();
  const calls = { graphql: 0 };

  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: { head: { sha: 'abc123' }, auto_merge: null, node_id: 'PR_node_1' } }),
        listReviews: async () => ({
          data: [{ state: 'APPROVED', user: { login: 'github-actions[bot]' } }],
        }),
      },
    },
    graphql: async () => {
      calls.graphql += 1;
      return {};
    },
  };

  await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'automerge' } },
    core,
    prNumber: 12,
  });

  assert.equal(calls.graphql, 1);
  assert.ok(infoMessages.some((msg) => msg.includes('PR #12: auto-merge enabled')));
});

test('enableAutomergeForApprovedPr skips when no approval', async () => {
  const { core, infoMessages } = makeCore();
  const calls = { graphql: 0, listReviews: 0 };

  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: { head: { sha: 'sha2' }, auto_merge: null, node_id: 'n2' } }),
        listReviews: async () => {
          calls.listReviews += 1;
          return { data: [{ state: 'COMMENTED', user: { login: 'github-actions[bot]' } }] };
        },
      },
    },
    graphql: async () => {
      calls.graphql += 1;
      return {};
    },
  };

  await run({
    github,
    context: { repo: { owner: 'elastic', repo: 'automerge' } },
    core,
    prNumber: 2,
  });

  assert.equal(calls.graphql, 0);
  assert.equal(calls.listReviews, 1);
  assert.ok(
    infoMessages.some((msg) => msg.includes('PR #2: skipped - no APPROVED review from github-actions[bot]'))
  );
});

test('enableAutomergeForApprovedPr throws when GraphQL enable fails', async () => {
  const { core, warnings } = makeCore();

  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: { head: { sha: 'abc123' }, auto_merge: null, node_id: 'PR_node_1' } }),
        listReviews: async () => ({
          data: [{ state: 'APPROVED', user: { login: 'github-actions[bot]' } }],
        }),
      },
    },
    graphql: async () => {
      throw new Error('GraphQL failure');
    },
  };

  await assert.rejects(
    run({
      github,
      context: { repo: { owner: 'elastic', repo: 'automerge' } },
      core,
      prNumber: 99,
    }),
    /PR #99 could not have auto-merge enabled/
  );

  assert.ok(warnings.some((msg) => msg.includes('PR #99: failed to enable auto-merge')));
});
