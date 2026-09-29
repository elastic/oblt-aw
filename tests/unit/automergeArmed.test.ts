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
  ARMED_COMMENT_MARKER,
  MERGE_READY_LABEL,
  buildArmedCommentBody,
  listArmedMergeReadyPrs,
  runDiscoverCandidates,
  upsertArmedComment,
} = require('../../scripts/obs/automergeArmed.ts');

function makeCore() {
  const infoMessages = [];
  return {
    core: { info: (msg) => infoMessages.push(msg) },
    infoMessages,
  };
}

test('buildArmedCommentBody includes marker and optional run URL', () => {
  const body = buildArmedCommentBody('https://example.test/run/1');
  assert.ok(body.includes(ARMED_COMMENT_MARKER));
  assert.ok(body.includes('armed'));
  assert.ok(body.includes('https://example.test/run/1'));
});

test('upsertArmedComment creates then updates', async () => {
  const { core } = makeCore();
  const comments = [];
  const github = {
    paginate: async () => comments.slice(),
    rest: {
      issues: {
        listComments: async () => ({ data: comments }),
        createComment: async ({ body }) => {
          const created = { id: 10, body };
          comments.push(created);
          return { data: created };
        },
        updateComment: async ({ comment_id, body }) => {
          const idx = comments.findIndex((c) => c.id === comment_id);
          comments[idx] = { ...comments[idx], body };
          return { data: comments[idx] };
        },
      },
    },
  };
  github.paginate = async (fn, opts) => {
    const res = await fn(opts);
    return res.data;
  };

  const first = await upsertArmedComment({
    github,
    owner: 'elastic',
    repo: 'r',
    prNumber: 1,
    runUrl: 'https://example.test/1',
    core,
  });
  assert.equal(first.created, true);
  assert.equal(comments.length, 1);
  assert.ok(comments[0].body.includes(ARMED_COMMENT_MARKER));

  const second = await upsertArmedComment({
    github,
    owner: 'elastic',
    repo: 'r',
    prNumber: 1,
    runUrl: 'https://example.test/2',
    core,
  });
  assert.equal(second.created, false);
  assert.equal(comments.length, 1);
  assert.ok(comments[0].body.includes('https://example.test/2'));
});

test('listArmedMergeReadyPrs returns only armed merge-ready opens', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        list: async () => ({
          data: [
            {
              number: 1,
              labels: [{ name: MERGE_READY_LABEL }],
              head: { sha: 'aaa' },
            },
            {
              number: 2,
              labels: [{ name: MERGE_READY_LABEL }],
              head: { sha: 'bbb' },
            },
            {
              number: 3,
              labels: [{ name: 'other' }],
              head: { sha: 'ccc' },
            },
          ],
        }),
      },
      issues: {
        listComments: async ({ issue_number }) => {
          if (issue_number === 1) {
            return { data: [{ id: 1, body: `${ARMED_COMMENT_MARKER}\narmed` }] };
          }
          return { data: [{ id: 2, body: 'not armed' }] };
        },
      },
    },
  };
  github.paginate = async (fn, opts) => {
    const res = await fn(opts);
    return res.data;
  };

  const found = await listArmedMergeReadyPrs({
    github,
    owner: 'elastic',
    repo: 'r',
    core,
  });
  assert.deepEqual(found, [{ pr_number: '1', head_sha: 'aaa' }]);
});

test('runDiscoverCandidates lists armed merge-ready PRs', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        list: async () => ({
          data: [
            {
              number: 9,
              labels: [{ name: MERGE_READY_LABEL }],
              head: { sha: 'sched' },
            },
          ],
        }),
      },
      issues: {
        listComments: async () => ({
          data: [{ id: 1, body: `${ARMED_COMMENT_MARKER}\narmed` }],
        }),
      },
    },
  };
  github.paginate = async (fn, opts) => {
    const res = await fn(opts);
    return res.data;
  };

  const { candidates } = await runDiscoverCandidates({
    github,
    context: { repo: { owner: 'elastic', repo: 'r' }, eventName: 'schedule' },
    core,
  });
  assert.deepEqual(candidates, [{ pr_number: '9', head_sha: 'sched' }]);
});
