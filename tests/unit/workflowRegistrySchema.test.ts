import { describe, it } from "node:test";
import assert from "node:assert";
import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { validateWorkflowRegistry } from "../../scripts/validateWorkflowRegistry.js";

const __dirname = dirname(fileURLToPath(import.meta.url));

describe("validateWorkflowRegistry", () => {
  it("returns false for missing workflows array", () => {
    assert.strictEqual(validateWorkflowRegistry({}), false);
    assert.strictEqual(validateWorkflowRegistry({ foo: [] }), false);
  });

  it("returns false for non-array workflows", () => {
    assert.strictEqual(validateWorkflowRegistry({ workflows: "not-array" }), false);
  });

  it("returns false for workflow missing required fields", () => {
    assert.strictEqual(
      validateWorkflowRegistry({
        workflows: [{ id: "a" }],
      }),
      false
    );
  });

  it("returns false for invalid maturity", () => {
    assert.strictEqual(
      validateWorkflowRegistry({
        workflows: [
          {
            id: "a",
            name: "A",
            description: "Desc",
            maturity: "invalid",
            default_enabled: true,
          },
        ],
      }),
      false
    );
  });

  it("returns true for valid registry", () => {
    const valid = {
      workflows: [
        {
          id: "a",
          name: "A",
          description: "Desc",
          maturity: "stable",
          default_enabled: true,
        },
      ],
    };
    assert.strictEqual(validateWorkflowRegistry(valid), true);
  });

  it("accepts all valid maturity values", () => {
    for (const m of ["stable", "early-adoption", "experimental"]) {
      assert.strictEqual(
        validateWorkflowRegistry({
          workflows: [
            {
              id: "a",
              name: "A",
              description: "Desc",
              maturity: m,
              default_enabled: true,
            },
          ],
        }),
        true
      );
    }
  });

  it("validates workflow-registry.json fixture", () => {
    const registryPath = join(__dirname, "..", "fixtures", "workflow-registry.json");
    const content = readFileSync(registryPath, "utf-8");
    const data = JSON.parse(content);
    assert.strictEqual(
      validateWorkflowRegistry(data),
      true,
      "workflow-registry fixture should pass schema validation"
    );
  });
});
