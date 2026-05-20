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

/**
 * Match a repository-relative path against a glob (supports `*` and `**`).
 */
function globPatternToRegExp(pattern: string): RegExp {
  const normalized = pattern.replace(/\\/g, '/').replace(/^\.\//, '');
  let re = '^';
  for (let i = 0; i < normalized.length; i += 1) {
    const ch = normalized[i];
    const next = normalized[i + 1];
    if (ch === '*' && next === '*') {
      const after = normalized[i + 2];
      if (after === '/') {
        re += '(?:.*/)?';
        i += 2;
      } else {
        re += '.*';
        i += 1;
      }
      continue;
    }
    if (ch === '*') {
      re += '[^/]*';
      continue;
    }
    if ('.+^${}()|[]\\'.includes(ch)) {
      re += `\\${ch}`;
      continue;
    }
    re += ch;
  }
  re += '$';
  return new RegExp(re);
}

function normalizePath(filePath: string): string {
  return filePath.replace(/\\/g, '/').replace(/^\.\//, '');
}

function matchPathGlob(filePath: string, pattern: string): boolean {
  const path = normalizePath(filePath);
  const pat = pattern.replace(/\\/g, '/');
  return globPatternToRegExp(pat).test(path);
}

function pathMatchesAnyGlob(filePath: string, patterns: string[]): boolean {
  return patterns.some((pattern) => matchPathGlob(filePath, pattern));
}

module.exports = { matchPathGlob, pathMatchesAnyGlob };
