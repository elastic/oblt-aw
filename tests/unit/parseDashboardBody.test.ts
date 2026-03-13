import { describe, it } from "node:test";
import assert from "node:assert";
import { parseDashboardBody } from "../../scripts/parseDashboardBody.js";

describe("parseDashboardBody", () => {
  it("returns all checked workflows when all are enabled", () => {
    const body = `
- [x] <!-- oblt-aw:dependency-review -->
- [x] <!-- oblt-aw:agent-suggestions -->
- [x] <!-- oblt-aw:autodoc -->
`;
    const result = parseDashboardBody(body);
    assert.deepStrictEqual(result.enabled_workflows, [
      "dependency-review",
      "agent-suggestions",
      "autodoc",
    ]);
  });

  it("returns empty array when all are unchecked", () => {
    const body = `
- [ ] <!-- oblt-aw:dependency-review -->
- [ ] <!-- oblt-aw:agent-suggestions -->
`;
    const result = parseDashboardBody(body);
    assert.deepStrictEqual(result.enabled_workflows, []);
  });

  it("returns only checked workflows for mixed state", () => {
    const body = `
- [x] <!-- oblt-aw:dependency-review -->
- [ ] <!-- oblt-aw:agent-suggestions -->
- [x] <!-- oblt-aw:autodoc -->
`;
    const result = parseDashboardBody(body);
    assert.deepStrictEqual(result.enabled_workflows, [
      "dependency-review",
      "autodoc",
    ]);
  });

  it("returns empty array for empty body", () => {
    const result = parseDashboardBody("");
    assert.deepStrictEqual(result.enabled_workflows, []);
  });

  it("ignores malformed lines without oblt-aw comment", () => {
    const body = `
- [x] some other text
- [ ] <!-- oblt-aw:valid-id -->
`;
    const result = parseDashboardBody(body);
    assert.deepStrictEqual(result.enabled_workflows, []);
  });

  it("handles long workflow ids", () => {
    const body = `- [x] <!-- oblt-aw:resource-not-accessible-by-integration-detector -->`;
    const result = parseDashboardBody(body);
    assert.deepStrictEqual(result.enabled_workflows, [
      "resource-not-accessible-by-integration-detector",
    ]);
  });
});
