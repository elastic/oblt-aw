'use strict';

const { parseMenuState } = require('./lib.js');

module.exports = async ({ context, core }) => {
  const body = context.payload.comment.body || '';
  const previousBody = context.payload.changes?.body?.from || '';

  const previousState = parseMenuState(previousBody);
  const currentState = parseMenuState(body);
  const triageTriggered = !previousState.triage.selected && currentState.triage.selected;
  const issueScopeTriggered =
    !previousState.issueScope.selected && currentState.issueScope.selected;

  core.setOutput('triage_triggered', String(triageTriggered));
  core.setOutput('issue_scope_triggered', String(issueScopeTriggered));
};
