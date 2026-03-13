/**
 * Parses a Control Plane Dashboard issue body and extracts enabled workflow IDs.
 * Format: - [x] <!-- oblt-aw:workflow-id --> (checked) or - [ ] <!-- oblt-aw:workflow-id --> (unchecked)
 */

const CHECKBOX_REGEX = /- \[([ x])\] <!-- oblt-aw:([a-z0-9-]+) -->/g;

export interface DashboardConfig {
  enabled_workflows: string[];
}

export function parseDashboardBody(body: string): DashboardConfig {
  const enabled_workflows: string[] = [];
  let match: RegExpExecArray | null;
  while ((match = CHECKBOX_REGEX.exec(body)) !== null) {
    const [, state, workflowId] = match;
    if (state === "x") {
      enabled_workflows.push(workflowId);
    }
  }
  return { enabled_workflows };
}
