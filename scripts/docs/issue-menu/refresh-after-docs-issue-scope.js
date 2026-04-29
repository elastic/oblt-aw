'use strict';

const { upsertMenuComment } = require('./lib.js');

module.exports = async ({ github, context, core }) => {
  const issueNumber = context.payload.issue.number;
  const progressUrl = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const issueScopeResult = process.env.ISSUE_SCOPE_RESULT || '';

  await upsertMenuComment({
    core,
    createIfMissing: false,
    github,
    context,
    issueNumber,
    statusOverrides: {
      issueScope: {
        conclusion:
          issueScopeResult === 'success'
            ? 'success'
            : issueScopeResult === 'cancelled'
              ? 'cancelled'
              : 'failure',
        detailsUrl: progressUrl,
        status: 'completed',
      },
    },
  });
};
