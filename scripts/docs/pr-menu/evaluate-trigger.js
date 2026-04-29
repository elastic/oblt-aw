'use strict';

const { parseMenuState } = require('./lib.js');

module.exports = async ({ context, core }) => {
  const body = context.payload.comment.body || '';
  const previousBody = context.payload.changes?.body?.from || '';

  const previousState = parseMenuState(previousBody);
  const currentState = parseMenuState(body);
  const docsReviewTriggered =
    !previousState.docsReview.selected && currentState.docsReview.selected;

  core.setOutput('docs_review_triggered', String(docsReviewTriggered));
};
