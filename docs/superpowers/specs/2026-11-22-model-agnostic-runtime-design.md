# Model-agnostic agent runtime for bede-core

Status: implemented and merged (bede PRs #82 to #88); first server deployment in
progress as of 2026-11-23 (`bede-data` running, `bede-core` not yet started).
See "As built" for changes since the design was approved.
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

Settings (`config.py`). Add `model`, `persona_path`, `agent_timeout_seconds` and
`max_agent_steps`, replacing the `claude_*` settings. `check_model_config()` runs at
startup and fails with a clear message if `MODEL` is unset, is not `provider:name`, or
the provider's key env var (for example `OPENROUTER_API_KEY`) is missing. Pydantic AI
reads the provider key from the environment itself, so there is no key setting.

Removed: Claude CLI install in the Dockerfile, the credentials mount and the
README sync/re-auth steps, and `claude_cli.py`. `AgentResult` keeps `auth_failure`,
which now means "the provider rejected the API key"; `bot.py` shows a key-rejected
notice instead of the re-auth instructions.

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
- Tool errors (path escape, missing file, write failure) are returned to the model as
  tool results so it can recover.
- Missing persona file: failed result naming the file, no crash.
- Model returns no usable answer (empty output): failed result suggesting a more
  capable model.

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

## As built (changes since approval)

Recorded 2026-11-23. The design above stands; these were added or settled during
build and first deployment.

- **Date tools.** `time_tools.py` adds `calculate_date`, `days_between` and
  `find_weekday`, in-process and deterministic, so a cheap model never does
  relative-date arithmetic itself (month-end clamping, leap years, "last
  Tuesday"). The persona tells the model to use them. No MCP dependency.
- **Privacy and cost routing (OpenRouter).** Every request sends
  `data_collection: deny`, `zdr: true` (zero-data-retention endpoints only) and
  `sort: price` ("Floor", cheapest first). Settings: `OPENROUTER_DENY_DATA_COLLECTION`,
  `OPENROUTER_ZDR`, `OPENROUTER_PROVIDER_SORT`, all defaulting on. A model with no
  ZDR host errors rather than falling back, so vet with `make bede-eval` before
  switching. OpenRouter has no Australian region (EU and US only, on paid plans);
  Bedrock or Vertex in a Sydney region via BYOK is the route if residency is required.
- **Startup checks.** `check_telegram_config` fails fast if the bot token or allowed
  user id is missing, alongside `check_model_config`.
- **Tool caps.** `read_file` reads at most 20,000 characters, `search` returns at
  most 50 hits of 300 characters and skips files over 2 MB.
- **Deployment.** `docker-compose.ai.yml` in home-server-stack runs `bede-init`
  (one-shot chown of `data/bede` to uid 1000), `bede-data` and `bede-core`. No
  Traefik route. Host env names are `BEDE_`-prefixed where they would clash
  (`BEDE_MODEL`, `BEDE_TELEGRAM_BOT_TOKEN`, `BEDE_ALLOWED_USER_ID`).
- **Eval set.** 12 prompts (8 vault and error-handling, 4 harder date prompts).
- **Sub-project status.** Item 2 (minimal `bede-data` redeploy) is done. Items 3
  and 4 are not started.

## Open items

- Default model: settled 2026-11-23 as `deepseek/deepseek-v4.1-flash` (8/8 on the
  eval, also under ZDR and Floor), fallback `anthropic/claude-haiku-5.5`.
  `openai/gpt-5-nano` is ruled out (invented content, made an unrequested write).
  One run per model, so this is a screening result. Revisit as prices and model
  names change.
- `max_agent_steps` stays at 15: no eval prompt needed more than 5 steps. Still to
  confirm against a real morning briefing.
- Set a hard monthly spend cap with OpenRouter before the first scheduled run.
  (The user's task; not yet confirmed done.)
- Create the morning-briefing schedule in `bede-data` (the schedules list is
  empty, so nothing fires), and provide the vault deploy key (the server has no
  SSH keypair).
