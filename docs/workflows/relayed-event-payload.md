# Relayed `github.event` payload contract

Consumer triggers relay the original webhook through `event-payload-json` → `ingress-event-payload-json`. The relay must stay within GitHub `workflow_dispatch` input size limits (see [workflow syntax — `on.workflow_dispatch.inputs`](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onworkflow_dispatchinputs)).

Preparation is implemented in [scripts/ingress_github_context.py](../../scripts/ingress_github_context.py) (`prepare_relayed_github_event_json`) and invoked from [`.github/actions/prepare-relayed-github-event`](../../.github/actions/prepare-relayed-github-event/action.yml) on each trigger run.

## Preparation modes

| Mode | When | What is sent |
|------|------|----------------|
| `passthrough` | Serialized full `github.event` ≤ budget | Unmodified webhook JSON |
| `slim` | Full event exceeds budget; slimmed fits | Only the attributes listed below (bloat removed) |
| `truncated` | Slimmed still exceeds budget | Slim shape; long **non-routing** strings shortened (see truncation) |

Budget defaults to 62,000 characters for the relay JSON string so sibling dispatch inputs (`trigger-source`, `event-name`, `caller-ref`, etc.) stay within the documented 65,535-character combined `workflow_dispatch` inputs payload.

## Attributes used by control-plane workflows

These paths are the **contract** for ingress routing, wrapper `if:` expressions, scripts, and relayed agent context. They are preserved in `slim` mode.

### Top-level

| Path | Used for |
|------|----------|
| `action` | Relayed event action; agent context |
| `inputs.issue_number` | Docs manual `workflow_dispatch` (issue menu) |
| `inputs.pull_request_number` | Docs manual `workflow_dispatch` (PR menu) |
| `state` | Buildkite status routing (`failure`) |
| `context` | Buildkite status routing (`buildkite` in context) |
| `sha` | Status events (optional) |
| `description` | Status events (optional; truncatable) |
| `target_url` | Status events (optional; preserved in slim, not truncated) |

### `pull_request`

| Path | Used for |
|------|----------|
| `pull_request.number` | Ingress routes, automerge, dependency-review, docs PR menu/collect |
| `pull_request.title` | Agent relayed context (truncatable) |
| `pull_request.head.ref` | PR checkout setup commands |
| `pull_request.head.sha` | Agent relayed context |
| `pull_request.user.login` | Ingress author allow-list gates |
| `pull_request.labels[].name` | Ingress label-based routing |

### `issue`

| Path | Used for |
|------|----------|
| `issue.number` | Ingress, security/triage, docs menus, PR-as-issue routes |
| `issue.title` | Agent relayed context (truncatable) |
| `issue.pull_request` | Distinguish issue vs PR (`null` vs `{}` / object) |
| `issue.labels[].name` | Ingress label and fixer/triage routing |

### `comment`

| Path | Used for |
|------|----------|
| `comment.id` | Agent relayed context |
| `comment.body` | `/ai` / `/ai implement` routing; docs menu marker `contains` (truncatable with prefix/suffix preserved) |
| `comment.author_association` | Author allow-list for issue comments |
| `comment.user.login` | Docs bot menu detection (`github-actions[bot]`) |

### `label` (issues `labeled` events)

| Path | Used for |
|------|----------|
| `label.name` | Security / res-not-accessible / fix-ready routing |

### `changes` (`issue_comment` edited)

| Path | Used for |
|------|----------|
| `changes.body.from` | Docs menu checkbox diff (`evaluate-trigger.js`) (truncatable) |

### `workflow_run`

| Path | Used for |
|------|----------|
| `workflow_run.id` | Docs PR AI menu concurrency / artifact download |
| `workflow_run.conclusion` | Docs ingress / PR menu (`success`) |
| `workflow_run.event` | Docs ingress (`pull_request`) |

### `discussion`

| Path | Used for |
|------|----------|
| `discussion.number` | Agent relayed context (when present) |

## Removed in `slim` mode (not used in workflows)

Examples: `pull_request.files`, `pull_request.commits`, `pull_request.body`, bulk repository metadata, check suites, reviews, and other webhook bloat. Agents must load these via GitHub MCP (see relayed context instructions in `ingress_github_context.py`).

## Truncation ( `truncated` mode only)

Applied only after `slim` when the payload is still over budget. Order:

1. `changes.body.from` — cap length (menu state is usually at the start of the body)
2. `comment.body` — cap length while preserving start and end segments for `/ai…` prefixes and HTML menu markers
3. `pull_request.title`, `issue.title` — cap length
4. `description` — cap length

Truncation does **not** remove routing-critical scalars (numbers, label names, `author_association`, `user.login`, `head.ref`, `head.sha`, etc.).

## References

- [oblt-aw ingress](oblt-aw-ingress.md) — `ingress-event-payload-json` input
- [aw-resolve-apm-assets](aw-resolve-apm-assets.md) — relayed context in agent prompts
- [oblt-aw client template](oblt-aw-client-template.md) — trigger relay
