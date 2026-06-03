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

/**
 * Original webhook payload for workflow_call routes that relay
 * ingress-event-payload-json. github-script context.payload is the
 * workflow_call envelope, not the consumer pull_request/issue event.
 */
function relayedPayload(context) {
  const raw = process.env.INGRESS_EVENT_JSON;
  if (typeof raw === 'string' && raw.trim() !== '') {
    return JSON.parse(raw);
  }
  return context.payload;
}

module.exports = { relayedPayload };
