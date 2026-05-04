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

const { upsertMenuComment } = require('./lib.js');

module.exports = async ({ github, context, core }) => {
  const pullRequestNumber = context.payload.issue.number;
  const progressUrl = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const docsReviewResult = process.env.DOCS_REVIEW_RESULT || '';

  await upsertMenuComment({
    core,
    createIfMissing: false,
    github,
    context,
    pullRequestNumber,
    statusOverrides: {
      docsReview: {
        conclusion:
          docsReviewResult === 'success'
            ? 'success'
            : docsReviewResult === 'cancelled'
              ? 'cancelled'
              : 'failure',
        detailsUrl: progressUrl,
        status: 'completed',
      },
    },
  });
};
