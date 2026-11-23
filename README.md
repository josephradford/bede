# Bede — Personal AI Assistant

Telegram bot and scheduled personal assistant, backed by any model API. Runs in Docker on the home server.

## Quick Start

### Prerequisites

1. **Telegram bot token** — create via [@BotFather](https://t.me/BotFather)
2. **Your Telegram user ID** — message [@userinfobot](https://t.me/userinfobot)
3. **A model API key** — for OpenRouter or another supported provider (see below)

### First-time setup

Bede is deployed from `docker-compose.ai.yml` in [home-server-stack](https://github.com/josephradford/home-server-stack). The names below are the ones that compose file reads from the server's `.env`.

**1. Add to `.env` on the server:**
```env
BEDE_TELEGRAM_BOT_TOKEN=your_token_here
BEDE_ALLOWED_USER_ID=your_numeric_id_here
VAULT_REPO=           # git URL for your Obsidian vault
VAULT_SSH_KEY_PATH=   # host path to SSH key (leave blank for HTTPS PAT)
```

**2. Choose a model and set its API key** (in the same `.env`):
```env
BEDE_MODEL=openrouter:<vendor>/<model>   # provider:name; edit this line to switch models
OPENROUTER_API_KEY=your_key_here
```
Bede checks both at startup (and the Telegram token and user id) and exits with a clear message if any is missing. Set a monthly spend cap in the provider's console. `make bede-eval` runs a set of test prompts against a model; run it before switching `BEDE_MODEL`.

Optional settings, all with defaults (set them in the same `.env`):

| Variable | Default | Effect |
|----------|---------|--------|
| `OPENROUTER_DENY_DATA_COLLECTION` | `true` | Only route to hosts that do not store or train on prompts |
| `OPENROUTER_ZDR` | `true` | Only route to zero-data-retention endpoints (a model with none will error) |
| `OPENROUTER_PROVIDER_SORT` | `price` | Cheapest host first ("Floor"); `latency`, `throughput`, `exacto`, or empty for OpenRouter's default |
| `MAX_AGENT_STEPS` | `15` | Model calls allowed per run before it stops |
| `AGENT_TIMEOUT_SECONDS` | `300` | Hard time limit per run |

These variables only affect OpenRouter models; other providers ignore the three `OPENROUTER_*` settings.

**3. Create your persona file** — it is personal, so it is not in git. In home-server-stack, copy the example from this repo to `data/bede/CLAUDE.md` (mounted read-only at `/app/CLAUDE.md`; bede-core will not start without it) and fill in your details:
```bash
cp CLAUDE.md.example ~/home-server-stack/data/bede/CLAUDE.md
# Edit it: set your name, location, timezone and role
```

**4. Start** (from the home-server-stack checkout on the server):
```bash
docker compose -f docker-compose.yml -f docker-compose.ai.yml up -d bede-data bede-core
docker logs -f bede-core
```

## Day-to-day Commands

Run from the home-server-stack checkout on the server:

```bash
AI="docker compose -f docker-compose.yml -f docker-compose.ai.yml"
$AI up -d bede-data bede-core    # Start Bede
$AI stop bede-core bede-data     # Stop
$AI restart bede-core            # Restart after editing .env
$AI ps                           # Container status
docker logs -f bede-core            # Tail bede-core logs
$AI pull bede-core bede-data && $AI up -d bede-core bede-data   # Update to the latest images
```

## Telegram Commands

- `/start` — greeting and available commands
- `/reset` — clear the current session (start a fresh conversation)

## Setting Up the Obsidian Vault

### HTTPS PAT (simpler)

Set `VAULT_REPO` to a URL with your PAT embedded:
```
VAULT_REPO=https://<PAT>@github.com/you/obsidian-vault.git
```

Leave `VAULT_SSH_KEY_PATH` blank.

### SSH key (private repo without PAT)

1. Generate a dedicated key on the server:
   ```bash
   ssh-keygen -t ed25519 -f ~/.ssh/bede_vault_key -N "" -C "bede@home-server"
   ```
2. Add the public key as a deploy key on your vault repo (read-only is fine).
3. Set in `.env`:
   ```
   VAULT_REPO=git@github.com:you/obsidian-vault.git
   VAULT_SSH_KEY_PATH=/home/user/.ssh/bede_vault_key
   ```

The vault is cloned on container start and pulled before each agent run.

## Architecture

```
docker-compose.ai.yml
├── bede-core           — Telegram bot + scheduler + session manager + agent runner (Pydantic AI)
├── bede-data           — FastAPI data layer + SQLite (port 8001)
├── bede-data-mcp       — MCP proxy to bede-data (port 8002)
├── bede-workspace-mcp  — Google Workspace MCP sidecar (port 8003)
└── bede-web            — Read-only dashboard (port 8080, nginx + API proxy)
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed diagrams, data flows, and service dependencies.

## Troubleshooting

### "API key rejected" in Telegram, or bede-core exits at startup

Check `BEDE_MODEL`, the matching provider key (e.g. `OPENROUTER_API_KEY`), `BEDE_TELEGRAM_BOT_TOKEN` and `BEDE_ALLOWED_USER_ID` in `.env`, then restart bede-core. Startup errors name the missing variable.

### "Stopped after N steps without a final answer"

The model kept calling tools without finishing. Raise `MAX_AGENT_STEPS`, or try a more capable model (check it with `make bede-eval`).

### Request errors after enabling ZDR or Floor

A model with no zero-data-retention host fails outright rather than falling back. Set `OPENROUTER_ZDR=false` for that model, or pick another, and check it with `make bede-eval`.

### "Unavailable tools this run: ..."

An MCP server (e.g. google-workspace) was unreachable. Check its container, then re-run the task.
