'use strict';

const { upsertMenuComment } = require('./lib.js');

module.exports = async ({ github, context, core }) => {
  const pullRequestNumber = context.payload.issue.number;
  const progressUrl = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;

  await upsertMenuComment({
    core,
    createIfMissing: false,
    github,
    context,
    pullRequestNumber,
    statusOverrides: {
      docsReview: { detailsUrl: progressUrl, status: 'in_progress' },
    },
  });
};
