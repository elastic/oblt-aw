'use strict';

const { upsertMenuComment } = require('./lib.js');

module.exports = async ({ github, context, core }) => {
  const issueNumber = context.payload.issue.number;
  const progressUrl = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const triageResult = process.env.TRIAGE_RESULT || '';

  await upsertMenuComment({
    core,
    createIfMissing: false,
    github,
    context,
    issueNumber,
    statusOverrides: {
      triage: {
        conclusion:
          triageResult === 'success'
            ? 'success'
            : triageResult === 'cancelled'
              ? 'cancelled'
              : 'failure',
        detailsUrl: progressUrl,
        status: 'completed',
      },
    },
  });
};
