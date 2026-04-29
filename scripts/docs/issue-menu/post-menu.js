'use strict';

const { upsertMenuComment } = require('./lib.js');

module.exports = async ({ github, context, core }) => {
  const workflowDispatchIssueNumber = context.payload.inputs?.issue_number;
  const issueNumber =
    context.eventName === 'workflow_dispatch'
      ? Number(workflowDispatchIssueNumber)
      : context.payload.issue.number;

  if (!issueNumber) {
    core.setFailed('Issue number is required for workflow_dispatch runs.');
    return;
  }

  await upsertMenuComment({ core, github, context, issueNumber });
};
