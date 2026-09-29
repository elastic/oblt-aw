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
  findArmedMergeReadyPrForSha,
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

test('findArmedMergeReadyPrForSha selects open merge-ready armed PR', async () => {
  const { core } = makeCore();
  const sha = 'abc123';
  const github = {
    rest: {
      repos: {
        listPullRequestsAssociatedWithCommit: async () => ({
          data: [
            {
              number: 7,
              state: 'open',
              labels: [{ name: MERGE_READY_LABEL }],
              head: { sha },
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

  const found = await findArmedMergeReadyPrForSha({
    github,
    owner: 'elastic',
    repo: 'r',
    sha,
    core,
  });
  assert.equal(found.prNumber, 7);
  assert.equal(found.headSha, sha);
});

test('findArmedMergeReadyPrForSha skips when not armed', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      repos: {
        listPullRequestsAssociatedWithCommit: async () => ({
          data: [
            {
              number: 8,
              state: 'open',
              labels: [{ name: MERGE_READY_LABEL }],
              head: { sha: 'deadbeef' },
            },
          ],
        }),
      },
      issues: {
        listComments: async () => ({ data: [{ id: 1, body: 'unrelated' }] }),
      },
    },
  };
  github.paginate = async (fn, opts) => {
    const res = await fn(opts);
    return res.data;
  };

  const found = await findArmedMergeReadyPrForSha({
    github,
    owner: 'elastic',
    repo: 'r',
    sha: 'deadbeef',
    core,
  });
  assert.equal(found.prNumber, null);
});
