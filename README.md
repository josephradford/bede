# Bede — Personal AI Assistant

Telegram bot and scheduled personal assistant, backed by any model API. Runs in Docker on the home server.

## Quick Start

### Prerequisites

1. **Telegram bot token** — create via [@BotFather](https://t.me/BotFather)
2. **Your Telegram user ID** — message [@userinfobot](https://t.me/userinfobot)
3. **A model API key** — for OpenRouter or another supported provider (see below)

### First-time setup

**1. Add to `.env` on the server:**
```env
TELEGRAM_BOT_TOKEN=your_token_here
ALLOWED_USER_ID=your_numeric_id_here
VAULT_REPO=           # git URL for your Obsidian vault
VAULT_SSH_KEY_PATH=   # host path to SSH key (leave blank for HTTPS PAT)
SESSION_TIMEOUT_MINUTES=10
```

**2. Choose a model and set its API key** (in the same `.env`):
```env
MODEL=openrouter:<vendor>/<model>   # provider:name; edit this line to switch models
OPENROUTER_API_KEY=your_key_here
```
Bede checks both at startup and exits with a clear message if either is missing. Set a monthly spend cap in the provider's console. `make bede-eval` runs a set of test prompts against the configured model.

**3. Create your persona file** — `bede/CLAUDE.md` is gitignored (it's personal). Copy the example and fill in your details:
```bash
cp bede/CLAUDE.md.example bede/CLAUDE.md
# Edit bede/CLAUDE.md — set your name, location, timezone, role, interests
```

**4. Build and start:**
```bash
make bede-build
make bede-start
make logs-bede
```

## Day-to-day Commands

```bash
make bede-start       # Start Bede services
make bede-stop        # Stop all containers
make bede-restart     # Restart all containers
make bede-status      # Show container status
make logs-bede        # Tail Bede logs
make bede-build       # Rebuild after code changes, then make bede-start
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

Check `MODEL` and the matching provider key (e.g. `OPENROUTER_API_KEY`) in `.env`, then restart bede-core. Startup errors name the missing variable.

### "Stopped after N steps without a final answer"

The model kept calling tools without finishing. Raise `MAX_AGENT_STEPS`, or try a more capable model (check it with `make bede-eval`).

### "Unavailable tools this run: ..."

An MCP server (e.g. google-workspace) was unreachable. Check its container, then re-run the task.
