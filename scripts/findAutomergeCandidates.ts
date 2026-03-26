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

module.exports.run = async function run({ github, context, mergeReadyLabel, allowedActor }) {
  const owner = context.repo.owner;
  const repo = context.repo.repo;

  const prs = await github.paginate(github.rest.pulls.list, {
    owner,
    repo,
    state: 'open',
    per_page: 100,
  });

  const qualifying = prs
    .filter((pr) => pr.user?.login === allowedActor)
    .filter((pr) => (pr.labels || []).some((label) => label.name === mergeReadyLabel))
    .filter((pr) => pr.draft === false)
    .filter((pr) => (pr.head?.repo?.full_name || '') === (pr.base?.repo?.full_name || ''))
    .filter((pr) => (pr.head?.ref || '') !== (pr.base?.ref || ''))
    .map((pr) => pr.number);

  // Keep matrix input stable for deterministic runs.
  const prNumbers = [...new Set(qualifying)].sort((a, b) => a - b);

  return { prNumbers };
};
