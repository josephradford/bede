# Model-agnostic agent runtime for bede-core

Status: design approved in conversation, awaiting written-spec review.
Scope: sub-project 1 of 4 (see Decomposition).

## Background and goal

Bede was decommissioned on 2026-07-06 because it never ran reliably. The main
cause was `bede-core` running the agent through `claude -p` with Claude Code
subscription OAuth credentials copied from the Mac. Those credentials expired or
were invalidated, and Bede stopped responding until re-authenticated by hand.
Using a consumer subscription login in a self-built harness is also not a
supported arrangement.

Goal: replace the Claude CLI subprocess with an in-process agent loop that
calls a paid model API, so that:

- there is no interactive login to expire,
- changing model or vendor is a one-line config edit,
- cheap models can be used where they are good enough, with a way to check.

Success criteria:

1. The morning briefing runs on schedule for two weeks with no manual auth.
2. Changing the `MODEL` environment variable switches the model with no code change.
3. A fixed eval set can be run against any candidate model before adopting it.

## Decomposition

Each item gets its own spec, plan and build. Only item 1 is specified here.

1. Model-agnostic runtime plus morning briefing (this spec).
2. Minimal `bede-data` redeploy (API only, from git history in home-server-stack).
   Prerequisite for 1 in production: `bede-core` loads schedules, task logs,
   memory and the scratchpad through `DataClient`.
3. Mac collectors restored (health export, screen time, Safari, podcasts).
4. Evening journal with health, location and usage data.

Deployment order: 2, then 1, then 3, then 4. Items 1 and 2 can be built in
either order, since 1's tests use fakes. Only the first end-to-end run of 1
needs 2 deployed.

## Non-goals

- Telegram chat sessions. First version is scheduled jobs only. No message
  history storage, truncation or summarisation.
- Removing the `bede-data` dependency from `bede-core`.
- Rewriting the scheduler, bot, or TaskRunner.
- The dashboard, ingest endpoints, and Mac collectors (items 2 to 4).
- A self-hosted gateway (LiteLLM). Pydantic AI can point at one later with no
  agent-code change.

## Design

### Components

`agent_runner.py` (new). Class `AgentRunner` with
`run(prompt, model, session_id=None, timeout=None) -> ClaudeResult`. The
`session_id` argument is accepted and ignored. The result type is kept so
`session_manager.py` and `bot.py` need minimal changes. It:

1. builds a Pydantic AI agent from a model string (`openrouter:<vendor>/<model>`),
2. loads the persona (`CLAUDE.md`) as the system prompt,
3. attaches vault tools and MCP toolsets,
4. enforces `max_agent_steps` and the timeout,
5. returns final text, or an error mapped onto existing result fields.

`vault_tools.py` (new). Tools: `list_dir`, `read_file`, `write_file`, `search`,
`commit_and_push`. All paths are resolved and confined to `/vault`; escapes are
rejected. No delete tool exists. This replaces the persona rule "don't delete
without confirmation" with a hard guarantee, and replaces
`--dangerously-skip-permissions`.

MCP. Toolsets are built from `mcp.json` using Pydantic AI's streamable-HTTP MCP
client: `personal-data` and `google-workspace`. The `browser` entry is removed
(its server is not part of the deployed services).

Settings (`config.py`). Add `model`, `openrouter_api_key`, `max_agent_steps`.
Rename the `claude_*` settings. A missing or invalid key fails at startup with a
clear message.

Removed: Claude CLI install in the Dockerfile, the credentials mount and the
README sync/re-auth steps, `auth_failure` handling in `bot.py`, and
`claude_cli.py` itself once nothing imports it.

### Data flow (scheduled run)

1. Scheduler fires; `TaskRunner` logs the start via `bede-data`.
2. `SessionManager` pulls the vault and builds the prompt: current date and
   time, memory context, task prompt.
3. `AgentRunner` runs the loop; the model calls vault and MCP tools until it
   produces a final answer or hits the step cap.
4. Result returns to `TaskRunner`, which sends to Telegram and logs completion.
   Vault writes are committed and pushed by the agent via `commit_and_push`.

### Error handling

- Timeout: run cancelled, `timed_out=True` (unchanged behaviour).
- Step cap: returns an explicit "stopped after N steps" message, not a partial answer.
- Provider errors (rate limit, 5xx): one retry with backoff, then a failed
  result through the existing Telegram error path. 401/403 produces a distinct
  message naming the API key.
- MCP server unreachable: run continues without those tools; the final message
  states which tools were unavailable so a briefing is never silently missing
  calendar data.
- Tool errors (path escape, missing file) are returned to the model as tool
  results so it can recover.

### Testing

- `vault_tools`: path confinement, write plus commit behaviour, absence of any
  delete capability.
- `AgentRunner`: Pydantic AI `TestModel` / `FunctionModel`, no network. Covers
  step cap, timeout, retry mapping, MCP failure.
- Eval set: about ten real prompts (morning briefing, journal-style vault
  writes, relative-date questions) run via `make bede-eval` against a chosen
  model. Manual, not CI. Used to vet a cheaper model before switching.
- Existing `session_manager` and scheduler tests stay, with the CLI fake
  replaced by a runner fake.

## Decisions and rationale

- Pydantic AI for the loop: provider-agnostic, typed, testable, native MCP client.
- OpenRouter first: one key and one bill across vendors. LiteLLM remains a
  later option behind the same interface.
- Start with a small-tier model from a major vendor, not the cheapest
  open-weight option. Tool-call reliability varies widely by model and host.
  Escalate or de-escalate per task using the eval set.
- Keep `bede-data` and `bede-core`'s existing plumbing (approach A): lowest
  risk, and items 3 and 4 need `bede-data` regardless.

## Open items

- Choose the default model after running the eval set (candidate small-tier
  models are compared at that point; prices and model names change often).
- Confirm the `max_agent_steps` default (starting guess: 15) against the
  morning-briefing eval.
- Set a hard monthly spend cap with OpenRouter before first deployment.
