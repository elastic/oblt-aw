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
