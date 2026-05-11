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

const { run } = require('../../scripts/obs/validateAutomergePr.ts');

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
