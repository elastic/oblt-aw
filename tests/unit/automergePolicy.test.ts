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
  MERGE_READY_LABEL,
  defaultAutomergePolicy,
  normalizeAutomergePolicy,
  hasTriggerLabel,
  isAuthorAllowedByPolicy,
  isForkAllowedByPolicy,
  isDayAllowedByPolicy,
} = require('../../scripts/obs/automergePolicy.ts');

test('normalizeAutomergePolicy always keeps merge-ready and defaults forks/authors', () => {
  const policy = normalizeAutomergePolicy({
    'trigger-labels': ['nightshift:risk-low'],
  });
  assert.deepEqual(policy.triggerLabels, [
    MERGE_READY_LABEL,
    'nightshift:risk-low',
  ]);
  assert.equal(policy.forks.mode, 'disabled');
  assert.equal(policy.authors.mode, 'allow-list');
  assert.deepEqual(policy.allowedDaysOfWeek, []);
});

test('normalizeAutomergePolicy keeps allowed-days-of-week and dedupes case', () => {
  const policy = normalizeAutomergePolicy({
    'allowed-days-of-week': ['Monday', 'friday', 'monday'],
  });
  assert.deepEqual(policy.allowedDaysOfWeek, ['monday', 'friday']);
});

test('normalizeAutomergePolicy rejects unknown weekday names', () => {
  assert.throws(
    () =>
      normalizeAutomergePolicy({
        'allowed-days-of-week': ['monady'],
      }),
    /unknown weekday/
  );
});

test('normalizeAutomergePolicy rejects non-array allowed-days-of-week', () => {
  assert.throws(
    () =>
      normalizeAutomergePolicy({
        'allowed-days-of-week': 'monday',
      }),
    /must be an array/
  );
});

test('isDayAllowedByPolicy treats empty list as unrestricted', () => {
  const policy = defaultAutomergePolicy();
  assert.equal(isDayAllowedByPolicy(policy, new Date('2026-11-20T12:00:00Z')), true);
});

test('isDayAllowedByPolicy allows and rejects UTC weekdays', () => {
  const policy = normalizeAutomergePolicy({
    'allowed-days-of-week': ['monday', 'tuesday', 'wednesday', 'thursday'],
  });
  // Friday 2026-11-20 UTC
  assert.equal(isDayAllowedByPolicy(policy, new Date('2026-11-20T12:00:00Z')), false);
  // Monday 2026-11-16 UTC
  assert.equal(isDayAllowedByPolicy(policy, new Date('2026-11-16T12:00:00Z')), true);
});

test('hasTriggerLabel accepts merge-ready or configured extras', () => {
  const policy = normalizeAutomergePolicy({
    'trigger-labels': ['nightshift:risk-low'],
  });
  assert.equal(hasTriggerLabel(policy, [MERGE_READY_LABEL]), true);
  assert.equal(hasTriggerLabel(policy, ['nightshift:risk-low']), true);
  assert.equal(hasTriggerLabel(policy, ['other']), false);
});

test('isAuthorAllowedByPolicy always allows control-plane bots', () => {
  const policy = normalizeAutomergePolicy({
    authors: { mode: 'author-association', 'author-associations': ['MEMBER'] },
  });
  assert.equal(
    isAuthorAllowedByPolicy(policy, {
      normalizedLogin: 'dependabot[bot]',
      authorAssociation: 'NONE',
      isControlPlaneBot: true,
    }),
    true
  );
});

test('isAuthorAllowedByPolicy author-association mode', () => {
  const policy = normalizeAutomergePolicy({
    authors: { mode: 'author-association', 'author-associations': ['MEMBER', 'OWNER'] },
  });
  assert.equal(
    isAuthorAllowedByPolicy(policy, {
      normalizedLogin: 'alice',
      authorAssociation: 'MEMBER',
      isControlPlaneBot: false,
    }),
    true
  );
  assert.equal(
    isAuthorAllowedByPolicy(policy, {
      normalizedLogin: 'alice',
      authorAssociation: 'CONTRIBUTOR',
      isControlPlaneBot: false,
    }),
    false
  );
});

test('isAuthorAllowedByPolicy allow-list extras', () => {
  const policy = normalizeAutomergePolicy({
    authors: { mode: 'allow-list', 'allow-list': ['custom-bot[bot]'] },
  });
  assert.equal(
    isAuthorAllowedByPolicy(policy, {
      normalizedLogin: 'custom-bot[bot]',
      authorAssociation: 'NONE',
      isControlPlaneBot: false,
    }),
    true
  );
  assert.equal(
    isAuthorAllowedByPolicy(policy, {
      normalizedLogin: 'human',
      authorAssociation: 'MEMBER',
      isControlPlaneBot: false,
    }),
    false
  );
});

test('isForkAllowedByPolicy disabled rejects forks', () => {
  const policy = defaultAutomergePolicy();
  assert.equal(
    isForkAllowedByPolicy(policy, {
      headFull: 'elastic/r',
      baseFull: 'elastic/r',
      authorAssociation: 'MEMBER',
    }),
    true
  );
  assert.equal(
    isForkAllowedByPolicy(policy, {
      headFull: 'alice/r',
      baseFull: 'elastic/r',
      authorAssociation: 'MEMBER',
    }),
    false
  );
});

test('isForkAllowedByPolicy author-association allows trusted forks', () => {
  const policy = normalizeAutomergePolicy({
    forks: {
      mode: 'author-association',
      'author-associations': ['MEMBER', 'OWNER'],
    },
  });
  assert.equal(
    isForkAllowedByPolicy(policy, {
      headFull: 'alice/r',
      baseFull: 'elastic/r',
      authorAssociation: 'MEMBER',
    }),
    true
  );
  assert.equal(
    isForkAllowedByPolicy(policy, {
      headFull: 'alice/r',
      baseFull: 'elastic/r',
      authorAssociation: 'NONE',
    }),
    false
  );
});
