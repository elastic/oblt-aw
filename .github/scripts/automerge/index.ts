export const MERGE_READY_LABEL = process.env.MERGE_READY_LABEL ?? "oblt-aw/ai/merge-ready";
export const ALLOWED_ACTOR = process.env.ALLOWED_ACTOR ?? "elastic-vault-github-plugin-prod[bot]";

export interface PullRequest {
  number: number;
  author: string;
  headRepo: string;
  baseRepo: string;
  headRef: string;
  baseRef: string;
  labels: string[];
  autoMergeEnabled: boolean;
  draft: boolean;
}

export interface CheckRun {
  status: string;
  conclusion: string | null;
}

export interface Review {
  state: string;
  user: { login: string };
}

export type CheckStatus = "passing" | "failing" | "pending" | "no_checks";

/**
 * Determines the overall check status based on a list of check runs.
 * Returns 'no_checks' when there are no check runs.
 * Returns 'pending' when some checks are still running.
 * Returns 'failing' when any completed check has a non-success/skipped/neutral conclusion.
 * Returns 'passing' when all checks are completed successfully.
 */
export function getCheckStatus(checkRuns: CheckRun[]): CheckStatus {
  const total = checkRuns.length;
  if (total === 0) return "no_checks";

  const completed = checkRuns.filter((c) => c.status === "completed");
  if (completed.length < total) return "pending";

  const failed = completed.filter(
    (c) =>
      c.conclusion !== "success" &&
      c.conclusion !== "skipped" &&
      c.conclusion !== "neutral"
  );
  if (failed.length > 0) return "failing";

  return "passing";
}

/**
 * Returns true when at least one review is an APPROVED review
 * submitted by github-actions[bot].
 */
export function isApprovedByActionsBot(reviews: Review[]): boolean {
  return reviews.some(
    (r) => r.state === "APPROVED" && r.user.login === "github-actions[bot]"
  );
}

export interface EligibilityResult {
  eligible: boolean;
  reason?: string;
}

/**
 * Evaluates all static (non-API) eligibility gates for a pull request.
 * Returns { eligible: true } when all gates pass, or
 * { eligible: false, reason: '...' } describing the first gate that failed.
 */
export function evaluateStaticGates(
  pr: PullRequest,
  allowedActor: string,
  mergeReadyLabel: string
): EligibilityResult {
  if (pr.author !== allowedActor) {
    return {
      eligible: false,
      reason: `author '${pr.author}' is not '${allowedActor}'`,
    };
  }

  if (!pr.labels.includes(mergeReadyLabel)) {
    return {
      eligible: false,
      reason: `missing label '${mergeReadyLabel}'`,
    };
  }

  if (pr.draft) {
    return { eligible: false, reason: "PR is in draft state" };
  }

  if (pr.headRepo !== pr.baseRepo) {
    return {
      eligible: false,
      reason: `head repo '${pr.headRepo}' differs from base repo '${pr.baseRepo}' (fork PR)`,
    };
  }

  if (pr.headRef === pr.baseRef) {
    return {
      eligible: false,
      reason: `head ref equals base ref ('${pr.headRef}')`,
    };
  }

  return { eligible: true };
}

/* -------------------------------------------------------------------------- */
/*  GitHub API helpers                                                          */
/* -------------------------------------------------------------------------- */

interface PullsListResponse {
  number: number;
  user: { login: string };
  head: { repo: { full_name: string } | null; ref: string; sha?: string };
  base: { repo: { full_name: string }; ref: string };
  labels: { name: string }[];
  auto_merge: unknown;
  draft: boolean;
}

interface CheckRunsResponse {
  check_runs: { status: string; conclusion: string | null }[];
}

interface ReviewResponse {
  state: string;
  user: { login: string };
}

interface GitHubClient {
  request: (
    route: string,
    params: Record<string, unknown>
  ) => Promise<unknown>;
  rest: {
    pulls: {
      list: (params: {
        owner: string;
        repo: string;
        state: string;
        per_page: number;
        page: number;
      }) => Promise<{ data: PullsListResponse[] }>;
      get: (params: {
        owner: string;
        repo: string;
        pull_number: number;
      }) => Promise<{ data: PullsListResponse & { head: { sha: string } } }>;
      listReviews: (params: {
        owner: string;
        repo: string;
        pull_number: number;
      }) => Promise<{ data: ReviewResponse[] }>;
    };
    checks: {
      listForRef: (params: {
        owner: string;
        repo: string;
        ref: string;
        per_page: number;
      }) => Promise<{ data: CheckRunsResponse }>;
    };
  };
}

async function fetchOpenPrs(
  github: GitHubClient,
  owner: string,
  repo: string
): Promise<PullRequest[]> {
  const prs: PullRequest[] = [];
  let page = 1;
  const perPage = 50;

  while (true) {
    const { data } = await github.rest.pulls.list({
      owner,
      repo,
      state: "open",
      per_page: perPage,
      page,
    });

    for (const pr of data) {
      prs.push({
        number: pr.number,
        author: pr.user.login,
        headRepo: pr.head.repo?.full_name ?? "",
        baseRepo: pr.base.repo?.full_name ?? "",
        headRef: pr.head.ref,
        baseRef: pr.base.ref,
        labels: pr.labels.map((l: { name: string }) => l.name),
        autoMergeEnabled: pr.auto_merge !== null,
        draft: pr.draft,
      });
    }

    if (data.length < perPage) break;
    page++;
  }

  return prs;
}

async function fetchCheckStatus(
  github: GitHubClient,
  owner: string,
  repo: string,
  prNumber: number
): Promise<CheckStatus> {
  const { data: prData } = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: prNumber,
  });

  const sha: string = prData.head.sha;

  const { data: checkData } = await github.rest.checks.listForRef({
    owner,
    repo,
    ref: sha,
    per_page: 100,
  });

  return getCheckStatus(checkData.check_runs);
}

async function fetchApprovalStatus(
  github: GitHubClient,
  owner: string,
  repo: string,
  prNumber: number
): Promise<boolean> {
  const { data: reviews } = await github.rest.pulls.listReviews({
    owner,
    repo,
    pull_number: prNumber,
  });

  return isApprovedByActionsBot(reviews);
}

/* -------------------------------------------------------------------------- */
/*  Main entry point                                                            */
/* -------------------------------------------------------------------------- */

export interface Core {
  info: (message: string) => void;
  warning: (message: string) => void;
  setFailed: (message: string) => void;
}

export interface RunParams {
  github: GitHubClient;
  context: { repo: { owner: string; repo: string } };
  core: Core;
}

export async function run({ github, context, core }: RunParams): Promise<void> {
  const { owner, repo } = context.repo;
  const mergeReadyLabel = process.env.MERGE_READY_LABEL ?? MERGE_READY_LABEL;
  const allowedActor = process.env.ALLOWED_ACTOR ?? ALLOWED_ACTOR;

  core.info(`Fetching open PRs with label '${mergeReadyLabel}'...`);

  const allPrs = await fetchOpenPrs(github, owner, repo);

  const qualifyingPrs: number[] = [];

  for (const pr of allPrs) {
    const prLabel = `PR #${pr.number}`;

    const staticResult = evaluateStaticGates(pr, allowedActor, mergeReadyLabel);
    if (!staticResult.eligible) {
      core.info(`${prLabel}: skipped — ${staticResult.reason}`);
      continue;
    }

    const checkStatus = await fetchCheckStatus(
      github,
      owner,
      repo,
      pr.number
    );

    if (checkStatus === "failing") {
      core.info(`${prLabel}: skipped — one or more required checks are failing`);
      continue;
    }
    if (checkStatus === "no_checks") {
      core.info(`${prLabel}: skipped — no check-runs found on this commit`);
      continue;
    }
    if (checkStatus === "pending") {
      core.info(`${prLabel}: skipped — checks are still running`);
      continue;
    }

    const approved = await fetchApprovalStatus(github, owner, repo, pr.number);
    if (!approved) {
      core.info(`${prLabel}: skipped — no APPROVED review from github-actions[bot]`);
      continue;
    }

    qualifyingPrs.push(pr.number);
  }

  if (qualifyingPrs.length === 0) {
    core.info("No qualifying PRs found — nothing to do.");
    return;
  }

  core.info(
    `Found ${qualifyingPrs.length} qualifying PR(s): ${qualifyingPrs.join(", ")}`
  );

  let failed = 0;

  for (const prNumber of qualifyingPrs) {
    const { data: prData } = await github.rest.pulls.get({
      owner,
      repo,
      pull_number: prNumber,
    });

    if (prData.auto_merge !== null) {
      core.info(`PR #${prNumber}: automerge already enabled — skipping`);
      continue;
    }

    core.info(`PR #${prNumber}: enabling automerge (squash)...`);
    try {
      await github.request(
        "PUT /repos/{owner}/{repo}/pulls/{pull_number}/automerge",
        {
          owner,
          repo,
          pull_number: prNumber,
          merge_method: "squash",
        }
      );
      core.info(`PR #${prNumber}: automerge enabled successfully`);
    } catch (err) {
      core.warning(`PR #${prNumber}: failed to enable automerge — ${err}`);
      failed++;
    }
  }

  if (failed > 0) {
    core.setFailed(`${failed} PR(s) could not have automerge enabled`);
  }
}
