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
  classifyChangedFiles,
  buildGateCommentBody,
  enabledAutomergeCollectionIds,
  parseEnabledWorkflowsJson,
} = require('../../scripts/obs/classifyAutomergeDependencyCollection.ts');

const COLLECTIONS = [
  {
    id: 'github-actions',
    'file-glob': ['.github/workflows/**'],
  },
  {
    id: 'python-dependencies',
    'file-glob': ['**/pyproject.toml'],
  },
];

const ENABLED = ['obs:automerge', 'obs:automerge:github-actions'];

test('classifyChangedFiles allows dashboard-enabled github-actions-only PR', () => {
  const outcome = classifyChangedFiles(
    ['.github/workflows/trigger-obs-aw-automerge.yml'],
    COLLECTIONS,
    enabledAutomergeCollectionIds(ENABLED)
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'github-actions',
  });
});

test('classifyChangedFiles allows dashboard-enabled pre-commit-only PR', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'pre-commit',
      'file-glob': ['.pre-commit-config.yaml'],
    },
  ];
  const enabled = [
    'obs:automerge',
    'obs:automerge:github-actions',
    'obs:automerge:pre-commit',
  ];
  const outcome = classifyChangedFiles(
    ['.pre-commit-config.yaml'],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'pre-commit',
  });
});

test('classifyChangedFiles rejects dashboard-disabled python collection', () => {
  const outcome = classifyChangedFiles(
    ['pyproject.toml'],
    COLLECTIONS,
    enabledAutomergeCollectionIds(ENABLED)
  );
  assert.deepEqual(outcome, {
    status: 'disabled',
    collectionId: 'python-dependencies',
  });
});

test('classifyChangedFiles is unclassified when no collection matches', () => {
  const outcome = classifyChangedFiles(
    ['README.md'],
    COLLECTIONS,
    enabledAutomergeCollectionIds(ENABLED)
  );
  assert.deepEqual(outcome, {
    status: 'unclassified',
    collectionId: null,
  });
});

test('classifyChangedFiles is ambiguous when multiple collections match', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'also-workflows',
      'file-glob': ['.github/workflows/**'],
    },
  ];
  const outcome = classifyChangedFiles(
    ['.github/workflows/x.yml'],
    collections,
    enabledAutomergeCollectionIds(ENABLED)
  );
  assert.equal(outcome.status, 'ambiguous');
  assert.equal(outcome.collectionIds.length, 2);
});

test('classifyChangedFiles allows dashboard-enabled terraform collection', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'terraform',
      'file-glob': [
        '**/*.tf',
        '**/*.tfvars',
        '**/*.tfvars.json',
        '**/.terraform.lock.hcl',
        '**/terragrunt.hcl',
        '**/.opentofu-version',
        '**/.terraform-version',
        '**/.terragrunt-version',
      ],
    },
  ];
  const enabled = ['obs:automerge', 'obs:automerge:terraform'];
  const outcome = classifyChangedFiles(
    [
      'environments/dev/main.tf',
      'environments/dev/vars.tfvars',
      'environments/dev/vars.tfvars.json',
      'environments/dev/.terraform.lock.hcl',
      'environments/dev/terragrunt.hcl',
      'environments/dev/.opentofu-version',
      'environments/dev/.terraform-version',
      'environments/dev/.terragrunt-version',
    ],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'terraform',
  });
});

test('classifyChangedFiles allows dashboard-enabled open-policy-agent collection', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'open-policy-agent',
      'file-glob': ['**/*.rego', '**/.opa-version', '**/opa.yaml', '**/opa.yml'],
    },
  ];
  const enabled = ['obs:automerge', 'obs:automerge:open-policy-agent'];
  const outcome = classifyChangedFiles(
    ['policies/authz.rego', '.opa-version'],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'open-policy-agent',
  });
});

const UPDATE_BEATS_GLOBS = [
  'NOTICE.txt',
  'NOTICE-fips.txt',
  '**/NOTICE.txt',
  '**/NOTICE-fips.txt',
  'go.mod',
  'go.sum',
  '**/go.mod',
  '**/go.sum',
  'beats',
];

const GO_DEPENDENCY_GLOBS = ['go.mod', 'go.sum', '**/go.mod', '**/go.sum'];
const VM_IMAGES_COLLECTION = {
  id: 'vm-images',
  'file-glob': [
    '.buildkite/**',
    '**/Dockerfile',
    '**/Dockerfile.*',
    '**/docker-compose.yml',
    '**/docker-compose.yaml',
    'testing/environments/snapshot.yml',
  ],
};

test('classifyChangedFiles allows dashboard-enabled update-beats collection', () => {
  const collections = [
    ...COLLECTIONS,
    { id: 'go-dependencies', 'file-glob': GO_DEPENDENCY_GLOBS },
    { id: 'update-beats', 'file-glob': UPDATE_BEATS_GLOBS },
  ];
  const enabled = ['obs:automerge', 'obs:automerge:update-beats'];
  const outcome = classifyChangedFiles(
    [
      'NOTICE-fips.txt',
      'NOTICE.txt',
      'beats',
      'go.mod',
      'go.sum',
      'internal/edot/go.mod',
      'internal/edot/go.sum',
    ],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'update-beats',
  });
});

test('classifyChangedFiles rejects dashboard-disabled update-beats collection', () => {
  const collections = [
    ...COLLECTIONS,
    { id: 'go-dependencies', 'file-glob': GO_DEPENDENCY_GLOBS },
    { id: 'update-beats', 'file-glob': UPDATE_BEATS_GLOBS },
  ];
  const enabled = ['obs:automerge', 'obs:automerge:go-dependencies'];
  const outcome = classifyChangedFiles(
    ['NOTICE.txt', 'NOTICE-fips.txt', 'go.mod', 'go.sum', 'beats'],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(outcome, {
    status: 'disabled',
    collectionId: 'update-beats',
  });
});

test('classifyChangedFiles allows dashboard-enabled vm-images snapshot.yml PR', () => {
  const collections = [...COLLECTIONS, VM_IMAGES_COLLECTION];
  const enabled = ['obs:automerge', 'obs:automerge:vm-images'];
  const outcome = classifyChangedFiles(
    ['testing/environments/snapshot.yml'],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'vm-images',
  });
});

test('classifyChangedFiles rejects dashboard-disabled vm-images snapshot.yml PR', () => {
  const collections = [...COLLECTIONS, VM_IMAGES_COLLECTION];
  const outcome = classifyChangedFiles(
    ['testing/environments/snapshot.yml'],
    collections,
    enabledAutomergeCollectionIds(ENABLED)
  );
  assert.deepEqual(outcome, {
    status: 'disabled',
    collectionId: 'vm-images',
  });
});

test('classifyChangedFiles allows dashboard-enabled package-version collection', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'package-version',
      'file-glob': ['.package-version', '**/.package-version'],
    },
  ];
  const enabled = ['obs:automerge', 'obs:automerge:package-version'];
  const outcome = classifyChangedFiles(
    ['nested/.package-version'],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'package-version',
  });

  const rootOutcome = classifyChangedFiles(
    ['.package-version'],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(rootOutcome, {
    status: 'allowed',
    collectionId: 'package-version',
  });
});

test('classifyChangedFiles allows dashboard-enabled root package-version collection', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'package-version',
      'file-glob': ['.package-version', '**/.package-version'],
    },
  ];
  const enabled = ['obs:automerge', 'obs:automerge:package-version'];
  const outcome = classifyChangedFiles(
    ['.package-version'],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'package-version',
  });
});

test('classifyChangedFiles rejects dashboard-disabled package-version collection', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'package-version',
      'file-glob': ['.package-version', '**/.package-version'],
    },
  ];
  const outcome = classifyChangedFiles(
    ['nested/.package-version'],
    collections,
    enabledAutomergeCollectionIds(ENABLED)
  );
  assert.deepEqual(outcome, {
    status: 'disabled',
    collectionId: 'package-version',
  });

  const rootOutcome = classifyChangedFiles(
    ['.package-version'],
    collections,
    enabledAutomergeCollectionIds(ENABLED)
  );
  assert.deepEqual(rootOutcome, {
    status: 'disabled',
    collectionId: 'package-version',
  });
});

test('classifyChangedFiles prefers go-dependencies over update-beats for go-only PRs', () => {
  const collections = [
    ...COLLECTIONS,
    { id: 'go-dependencies', 'file-glob': GO_DEPENDENCY_GLOBS },
    { id: 'update-beats', 'file-glob': UPDATE_BEATS_GLOBS },
  ];
  const enabled = [
    'obs:automerge',
    'obs:automerge:go-dependencies',
    'obs:automerge:update-beats',
  ];
  const outcome = classifyChangedFiles(
    ['go.mod', 'go.sum', 'internal/edot/go.mod'],
    collections,
    enabledAutomergeCollectionIds(enabled)
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'go-dependencies',
  });
});

test('enabledAutomergeCollectionIds returns empty when parent disabled', () => {
  const enabled = ['obs:automerge:github-actions'];
  assert.deepEqual(enabledAutomergeCollectionIds(enabled), []);
});

test('parseEnabledWorkflowsJson handles invalid input', () => {
  assert.deepEqual(parseEnabledWorkflowsJson(''), []);
  assert.deepEqual(parseEnabledWorkflowsJson('not-json'), []);
});

test('buildGateCommentBody includes disabled collection and enabled list', () => {
  const body = buildGateCommentBody(
    { status: 'disabled', collectionId: 'python-dependencies' },
    ['pyproject.toml'],
    enabledAutomergeCollectionIds(ENABLED)
  );
  assert.match(body, /python-dependencies/);
  assert.match(body, /github-actions/);
  assert.match(body, /dependency-collection-gate/);
  assert.match(body, /Control Plane Dashboard/);
  assert.match(body, /docs\/guides\/user\/automerge-services\.md/);
});
