'use strict';

const { upsertMenuComment } = require('./lib.js');

module.exports = async ({ github, context, core }) => {
  const workflowDispatchPrNumber = context.payload.inputs?.pull_request_number;
  const pullRequestNumber =
    context.eventName === 'workflow_dispatch'
      ? Number(workflowDispatchPrNumber)
      : context.payload.pull_request.number;

  if (!pullRequestNumber) {
    core.setFailed('Pull request number is required for workflow_dispatch runs.');
    return;
  }

  await upsertMenuComment({ core, github, context, pullRequestNumber });
};
