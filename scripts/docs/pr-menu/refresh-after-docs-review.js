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
