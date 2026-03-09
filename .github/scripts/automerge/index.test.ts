import {
  getCheckStatus,
  isApprovedByActionsBot,
  evaluateStaticGates,
  CheckRun,
  Review,
  PullRequest,
} from "./index";

/* -------------------------------------------------------------------------- */
/*  getCheckStatus                                                              */
/* -------------------------------------------------------------------------- */

describe("getCheckStatus", () => {
  it("returns 'no_checks' when the list is empty", () => {
    expect(getCheckStatus([])).toBe("no_checks");
  });

  it("returns 'pending' when at least one check is not completed", () => {
    const checks: CheckRun[] = [
      { status: "completed", conclusion: "success" },
      { status: "in_progress", conclusion: null },
    ];
    expect(getCheckStatus(checks)).toBe("pending");
  });

  it("returns 'failing' when a completed check has a failing conclusion", () => {
    const checks: CheckRun[] = [
      { status: "completed", conclusion: "success" },
      { status: "completed", conclusion: "failure" },
    ];
    expect(getCheckStatus(checks)).toBe("failing");
  });

  it("treats 'timed_out' conclusion as failing", () => {
    const checks: CheckRun[] = [
      { status: "completed", conclusion: "timed_out" },
    ];
    expect(getCheckStatus(checks)).toBe("failing");
  });

  it("treats 'action_required' conclusion as failing", () => {
    const checks: CheckRun[] = [
      { status: "completed", conclusion: "action_required" },
    ];
    expect(getCheckStatus(checks)).toBe("failing");
  });

  it("returns 'passing' when all checks are completed with success/skipped/neutral", () => {
    const checks: CheckRun[] = [
      { status: "completed", conclusion: "success" },
      { status: "completed", conclusion: "skipped" },
      { status: "completed", conclusion: "neutral" },
    ];
    expect(getCheckStatus(checks)).toBe("passing");
  });

  it("returns 'passing' for a single successful check", () => {
    const checks: CheckRun[] = [
      { status: "completed", conclusion: "success" },
    ];
    expect(getCheckStatus(checks)).toBe("passing");
  });

  it("returns 'failing' even when mixed with successful checks", () => {
    const checks: CheckRun[] = [
      { status: "completed", conclusion: "success" },
      { status: "completed", conclusion: "cancelled" },
      { status: "completed", conclusion: "skipped" },
    ];
    expect(getCheckStatus(checks)).toBe("failing");
  });
});

/* -------------------------------------------------------------------------- */
/*  isApprovedByActionsBot                                                      */
/* -------------------------------------------------------------------------- */

describe("isApprovedByActionsBot", () => {
  it("returns false for an empty review list", () => {
    expect(isApprovedByActionsBot([])).toBe(false);
  });

  it("returns true when github-actions[bot] approved the PR", () => {
    const reviews: Review[] = [
      { state: "APPROVED", user: { login: "github-actions[bot]" } },
    ];
    expect(isApprovedByActionsBot(reviews)).toBe(true);
  });

  it("returns false when github-actions[bot] submitted a non-APPROVED review", () => {
    const reviews: Review[] = [
      { state: "CHANGES_REQUESTED", user: { login: "github-actions[bot]" } },
    ];
    expect(isApprovedByActionsBot(reviews)).toBe(false);
  });

  it("returns false when only a human user approved the PR", () => {
    const reviews: Review[] = [
      { state: "APPROVED", user: { login: "some-human" } },
    ];
    expect(isApprovedByActionsBot(reviews)).toBe(false);
  });

  it("returns true when github-actions[bot] approved among multiple reviews", () => {
    const reviews: Review[] = [
      { state: "CHANGES_REQUESTED", user: { login: "reviewer-1" } },
      { state: "APPROVED", user: { login: "github-actions[bot]" } },
      { state: "APPROVED", user: { login: "reviewer-2" } },
    ];
    expect(isApprovedByActionsBot(reviews)).toBe(true);
  });
});

/* -------------------------------------------------------------------------- */
/*  evaluateStaticGates                                                         */
/* -------------------------------------------------------------------------- */

const BASE_PR: PullRequest = {
  number: 42,
  author: "elastic-vault-github-plugin-prod[bot]",
  headRepo: "elastic/my-repo",
  baseRepo: "elastic/my-repo",
  headRef: "feature/my-branch",
  baseRef: "main",
  labels: ["oblt-aw/ai/merge-ready"],
  autoMergeEnabled: false,
  draft: false,
};

const ALLOWED_ACTOR = "elastic-vault-github-plugin-prod[bot]";
const MERGE_READY_LABEL = "oblt-aw/ai/merge-ready";

describe("evaluateStaticGates", () => {
  it("returns eligible for a fully qualifying PR", () => {
    expect(evaluateStaticGates(BASE_PR, ALLOWED_ACTOR, MERGE_READY_LABEL)).toEqual({
      eligible: true,
    });
  });

  it("rejects when the author is not the allowed actor", () => {
    const pr = { ...BASE_PR, author: "some-other-user" };
    const result = evaluateStaticGates(pr, ALLOWED_ACTOR, MERGE_READY_LABEL);
    expect(result.eligible).toBe(false);
    expect(result.reason).toContain("author");
  });

  it("rejects when the merge-ready label is missing", () => {
    const pr = { ...BASE_PR, labels: ["some-other-label"] };
    const result = evaluateStaticGates(pr, ALLOWED_ACTOR, MERGE_READY_LABEL);
    expect(result.eligible).toBe(false);
    expect(result.reason).toContain("label");
  });

  it("rejects when the PR is a draft", () => {
    const pr = { ...BASE_PR, draft: true };
    const result = evaluateStaticGates(pr, ALLOWED_ACTOR, MERGE_READY_LABEL);
    expect(result.eligible).toBe(false);
    expect(result.reason).toContain("draft");
  });

  it("rejects when the PR comes from a fork (different head/base repos)", () => {
    const pr = { ...BASE_PR, headRepo: "fork-user/my-repo" };
    const result = evaluateStaticGates(pr, ALLOWED_ACTOR, MERGE_READY_LABEL);
    expect(result.eligible).toBe(false);
    expect(result.reason).toContain("fork PR");
  });

  it("rejects when head ref equals base ref", () => {
    const pr = { ...BASE_PR, headRef: "main" };
    const result = evaluateStaticGates(pr, ALLOWED_ACTOR, MERGE_READY_LABEL);
    expect(result.eligible).toBe(false);
    expect(result.reason).toContain("head ref equals base ref");
  });

  it("rejects on the first failing gate (author check before label check)", () => {
    const pr = {
      ...BASE_PR,
      author: "wrong-user",
      labels: [],
    };
    const result = evaluateStaticGates(pr, ALLOWED_ACTOR, MERGE_READY_LABEL);
    expect(result.eligible).toBe(false);
    expect(result.reason).toContain("author");
  });
});
