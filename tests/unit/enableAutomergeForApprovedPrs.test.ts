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

const { run } = require('../../scripts/enableAutomergeForApprovedPrs.ts');

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

test('enableAutomergeForApprovedPrs exits early when no PR numbers are provided', async () => {
  const { core, infoMessages } = makeCore();

  await run({
    github: {},
    context: { repo: { owner: 'elastic', repo: 'automerge' } },
    core,
    prNumbers: [],
  });

  assert.equal(infoMessages[0], 'No PRs provided for auto-merge enablement.');
});

test('enableAutomergeForApprovedPrs enables auto-merge when checks pass and approval exists', async () => {
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
      checks: {
        listForRef: async () => ({
          data: {
            check_runs: [{ status: 'completed', conclusion: 'success' }],
          },
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
    prNumbers: [12],
  });

  assert.equal(calls.graphql, 1);
  assert.ok(infoMessages.some((msg) => msg.includes('PR #12: auto-merge enabled')));
});

test('enableAutomergeForApprovedPrs skips PRs without passing checks or approval', async () => {
  const { core, infoMessages } = makeCore();
  const calls = { graphql: 0, listReviews: 0 };

  const github = {
    rest: {
      pulls: {
        get: async ({ pull_number }) => ({
          data: { head: { sha: `sha-${pull_number}` }, auto_merge: null, node_id: `node-${pull_number}` },
        }),
        listReviews: async ({ pull_number }) => {
          calls.listReviews += 1;
          if (pull_number === 2) {
            return { data: [{ state: 'COMMENTED', user: { login: 'github-actions[bot]' } }] };
          }
          return { data: [] };
        },
      },
      checks: {
        listForRef: async ({ ref }) => {
          if (ref === 'sha-1') {
            return { data: { check_runs: [{ status: 'completed', conclusion: 'failure' }] } };
          }
          return { data: { check_runs: [{ status: 'completed', conclusion: 'success' }] } };
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
    prNumbers: [1, 2],
  });

  assert.equal(calls.graphql, 0);
  assert.equal(calls.listReviews, 1);
  assert.ok(infoMessages.some((msg) => msg.includes("PR #1: skipped - check status is 'failing'")));
  assert.ok(
    infoMessages.some((msg) => msg.includes('PR #2: skipped - no APPROVED review from github-actions[bot]'))
  );
});

test('enableAutomergeForApprovedPrs throws when one or more auto-merge operations fail', async () => {
  const { core, warnings } = makeCore();

  const github = {
    rest: {
      pulls: {
        get: async () => ({ data: { head: { sha: 'abc123' }, auto_merge: null, node_id: 'PR_node_1' } }),
        listReviews: async () => ({
          data: [{ state: 'APPROVED', user: { login: 'github-actions[bot]' } }],
        }),
      },
      checks: {
        listForRef: async () => ({
          data: {
            check_runs: [{ status: 'completed', conclusion: 'success' }],
          },
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
      prNumbers: [99],
    }),
    /1 PR\(s\) could not have auto-merge enabled/
  );

  assert.ok(warnings.some((msg) => msg.includes('PR #99: failed to enable auto-merge')));
});
