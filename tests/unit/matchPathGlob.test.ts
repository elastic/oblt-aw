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

const { matchPathGlob, pathMatchesAnyGlob } = require('../../scripts/obs/lib/matchPathGlob.ts');

test('matchPathGlob matches workflow paths', () => {
  assert.equal(
    matchPathGlob('.github/workflows/trigger-oblt-aw-automerge.yml', '.github/workflows/**'),
    true
  );
  assert.equal(matchPathGlob('README.md', '.github/workflows/**'), false);
});

test('matchPathGlob matches action manifests', () => {
  assert.equal(matchPathGlob('composite/action.yml', '**/action.yml'), true);
});

test('pathMatchesAnyGlob accepts multiple patterns', () => {
  assert.equal(
    pathMatchesAnyGlob('go.mod', ['**/pyproject.toml', 'go.mod']),
    true
  );
});
