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
  activeCollectionIds,
} = require('../../scripts/obs/classifyAutomergeDependencyCollection.ts');

const COLLECTIONS = [
  {
    id: 'github-actions',
    active: true,
    'file-glob': ['.github/workflows/**'],
  },
  {
    id: 'python-dependencies',
    active: false,
    'file-glob': ['**/pyproject.toml'],
  },
];

test('classifyChangedFiles allows active github-actions-only PR', () => {
  const outcome = classifyChangedFiles(
    ['.github/workflows/trigger-oblt-aw-automerge.yml'],
    COLLECTIONS
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'github-actions',
  });
});

test('classifyChangedFiles allows active pre-commit-only PR', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'pre-commit',
      active: true,
      'file-glob': ['.pre-commit-config.yaml'],
    },
  ];
  const outcome = classifyChangedFiles(['.pre-commit-config.yaml'], collections);
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'pre-commit',
  });
});

test('classifyChangedFiles rejects inactive python collection', () => {
  const outcome = classifyChangedFiles(['pyproject.toml'], COLLECTIONS);
  assert.deepEqual(outcome, {
    status: 'inactive',
    collectionId: 'python-dependencies',
  });
});

test('classifyChangedFiles is unclassified when no collection matches', () => {
  const outcome = classifyChangedFiles(['README.md'], COLLECTIONS);
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
      active: false,
      'file-glob': ['.github/workflows/**'],
    },
  ];
  const outcome = classifyChangedFiles(
    ['.github/workflows/x.yml'],
    collections
  );
  assert.equal(outcome.status, 'ambiguous');
  assert.equal(outcome.collectionIds.length, 2);
});

test('classifyChangedFiles allows active terraform collection', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'terraform',
      active: true,
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
    collections
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'terraform',
  });
});

test('classifyChangedFiles allows active open-policy-agent collection', () => {
  const collections = [
    ...COLLECTIONS,
    {
      id: 'open-policy-agent',
      active: true,
      'file-glob': ['**/*.rego', '**/.opa-version', '**/opa.yaml', '**/opa.yml'],
    },
  ];
  const outcome = classifyChangedFiles(
    ['policies/authz.rego', '.opa-version'],
    collections
  );
  assert.deepEqual(outcome, {
    status: 'allowed',
    collectionId: 'open-policy-agent',
  });
});

test('buildGateCommentBody includes inactive collection and active list', () => {
  const body = buildGateCommentBody(
    { status: 'inactive', collectionId: 'python-dependencies' },
    ['pyproject.toml'],
    activeCollectionIds(COLLECTIONS)
  );
  assert.match(body, /python-dependencies/);
  assert.match(body, /github-actions/);
  assert.match(body, /dependency-collection-gate/);
});
