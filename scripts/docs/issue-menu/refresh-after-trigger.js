'use strict';

const { upsertMenuComment } = require('./lib.js');

module.exports = async ({ github, context, core }) => {
  const issueNumber = context.payload.issue.number;
  const progressUrl = `${context.serverUrl}/${context.repo.owner}/${context.repo.repo}/actions/runs/${context.runId}`;
  const statusOverrides = {};

  if (process.env.TRIAGE_TRIGGERED === 'true') {
    statusOverrides.triage = { detailsUrl: progressUrl, status: 'in_progress' };
  }

  if (process.env.ISSUE_SCOPE_TRIGGERED === 'true') {
    statusOverrides.issueScope = { detailsUrl: progressUrl, status: 'in_progress' };
  }

  await upsertMenuComment({
    core,
    createIfMissing: false,
    github,
    context,
    issueNumber,
    statusOverrides,
  });
};
