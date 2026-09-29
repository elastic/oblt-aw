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
  classifyMergeError,
  mergePullRequestRest,
} = require('../../scripts/obs/mergeAutomergePrRest.ts');

function makeCore() {
  const infoMessages = [];
  return {
    core: { info: (msg) => infoMessages.push(msg) },
    infoMessages,
  };
}

test('classifyMergeError maps pending required status to pending_checks', () => {
  const err = {
    status: 405,
    message: 'Required status check "buildkite/elastic-agent" is pending.',
  };
  assert.equal(classifyMergeError(err).result, 'pending_checks');
});

test('classifyMergeError maps already merged to merged', () => {
  const err = {
    status: 405,
    message: 'Pull Request is not mergeable: already been merged',
  };
  assert.equal(classifyMergeError(err).result, 'merged');
});

test('classifyMergeError maps 409 to sha_mismatch', () => {
  assert.equal(classifyMergeError({ status: 409, message: 'Head changed' }).result, 'sha_mismatch');
});

test('mergePullRequestRest returns merged on success', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        merge: async () => ({ data: { merged: true } }),
      },
    },
  };
  const r = await mergePullRequestRest({
    github,
    owner: 'elastic',
    repo: 'r',
    prNumber: 1,
    headSha: 'abc',
    core,
  });
  assert.equal(r.result, 'merged');
});

test('mergePullRequestRest returns pending_checks on 405 pending', async () => {
  const { core } = makeCore();
  const github = {
    rest: {
      pulls: {
        merge: async () => {
          const err = new Error('Required status check "buildkite/x" is pending.');
          err.status = 405;
          throw err;
        },
      },
    },
  };
  const r = await mergePullRequestRest({
    github,
    owner: 'elastic',
    repo: 'r',
    prNumber: 1,
    headSha: 'abc',
    core,
  });
  assert.equal(r.result, 'pending_checks');
});
