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

'use strict';

const { relayedPayload } = require('../lib/relayed-event.js');
const { parseMenuState } = require('./lib.js');

module.exports = async ({ github, context, core }) => {
  const payload = relayedPayload(context);
  const pullNumber = payload.issue?.number;
  if (!pullNumber) {
    core.setFailed('Pull request number is required.');
    return;
  }
  const { data: pullRequest } = await github.rest.pulls.get({
    owner: context.repo.owner,
    repo: context.repo.repo,
    pull_number: pullNumber,
  });
  const baseRepoFullName = `${context.repo.owner}/${context.repo.repo}`;
  const isForkPR = pullRequest.head.repo.full_name !== baseRepoFullName;
  if (isForkPR) {
    let isOrgMember = false;
    try {
      const { status } = await github.rest.orgs.checkMembershipForUser({
        org: context.repo.owner,
        username: context.actor,
      });
      isOrgMember = status === 204;
    } catch {
      isOrgMember = false;
    }
    if (!isOrgMember) {
      core.info('Fork PR: skipping docs review for non-org member.');
      core.setOutput('docs_review_triggered', 'false');
      return;
    }
  }

  const body = payload.comment?.body || '';
  const previousBody = payload.changes?.body?.from || '';

  const previousState = parseMenuState(previousBody);
  const currentState = parseMenuState(body);
  const docsReviewTriggered =
    !previousState.docsReview.selected && currentState.docsReview.selected;

  core.setOutput('docs_review_triggered', String(docsReviewTriggered));
};
