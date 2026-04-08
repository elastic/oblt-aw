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
  filterCheckRunsExcludingCurrentWorkflow,
  checkRunGateStatus,
} = require('../../scripts/automergeCheckRunGate.ts');

const selfRun = (runId, jobPath = 'job/1') => ({
  status: 'in_progress',
  conclusion: null,
  details_url: `https://github.com/o/r/actions/runs/${runId}/${jobPath}`,
});

test('filterCheckRunsExcludingCurrentWorkflow removes checks for current run id', () => {
  const runs = [
    selfRun(99),
    { status: 'completed', conclusion: 'success', details_url: 'https://github.com/o/r/actions/runs/100/job/1' },
  ];
  const filtered = filterCheckRunsExcludingCurrentWorkflow(runs, 99);
  assert.equal(filtered.length, 1);
  assert.equal(filtered[0].details_url, 'https://github.com/o/r/actions/runs/100/job/1');
});

test('filterCheckRunsExcludingCurrentWorkflow is no-op without run id', () => {
  const runs = [selfRun(99)];
  assert.deepEqual(filterCheckRunsExcludingCurrentWorkflow(runs, undefined), runs);
  assert.deepEqual(filterCheckRunsExcludingCurrentWorkflow(runs, NaN), runs);
});

test('checkRunGateStatus passes when only current-run checks are pending', () => {
  const runs = [
    { status: 'completed', conclusion: 'success', details_url: 'https://github.com/o/r/actions/runs/10/job/1' },
    selfRun(20),
  ];
  assert.equal(checkRunGateStatus(runs, 20), 'passing');
});

test('checkRunGateStatus still pending when other checks are in progress', () => {
  const runs = [
    { status: 'queued', conclusion: null, details_url: 'https://github.com/o/r/actions/runs/10/job/1' },
    selfRun(20),
  ];
  assert.equal(checkRunGateStatus(runs, 20), 'pending');
});
