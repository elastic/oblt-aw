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
