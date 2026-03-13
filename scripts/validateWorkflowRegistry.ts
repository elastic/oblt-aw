/**
 * Validates workflow-registry.json schema.
 */

const VALID_MATURITY = ["stable", "early-adoption", "experimental"] as const;

export interface WorkflowEntry {
  id: string;
  name: string;
  description: string;
  maturity: string;
  default_enabled: boolean;
}

export interface WorkflowRegistry {
  workflows: WorkflowEntry[];
}

export function validateWorkflowRegistry(data: unknown): data is WorkflowRegistry {
  if (!data || typeof data !== "object") return false;
  const obj = data as Record<string, unknown>;
  if (!Array.isArray(obj.workflows)) return false;
  for (const w of obj.workflows) {
    if (typeof w !== "object" || w === null) return false;
    const entry = w as Record<string, unknown>;
    if (typeof entry.id !== "string") return false;
    if (typeof entry.name !== "string") return false;
    if (typeof entry.description !== "string") return false;
    if (typeof entry.maturity !== "string") return false;
    if (!VALID_MATURITY.includes(entry.maturity as (typeof VALID_MATURITY)[number]))
      return false;
    if (typeof entry.default_enabled !== "boolean") return false;
  }
  return true;
}
