"""
Bede — Telegram bot wrapping Claude Code CLI.

Each message runs `claude -p` as a subprocess. Multi-turn conversations
reuse the same session via --resume within a configurable timeout window.
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import time

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from scheduler import reload as scheduler_reload, setup_scheduler, _parse_tasks, _run_task, _running_tasks, cancel_all_tasks
from utils import md_to_html

load_dotenv()



logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)
log = logging.getLogger(__name__)

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USER_ID = int(os.environ["ALLOWED_USER_ID"])
CLAUDE_WORKDIR = os.environ.get("CLAUDE_WORKDIR", "/app")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
SESSION_TIMEOUT_SECS = int(os.environ.get("SESSION_TIMEOUT_MINUTES", "10")) * 60
INTERACTIVE_IDLE_TIMEOUT_SECS = int(os.environ.get("INTERACTIVE_IDLE_TIMEOUT_MINUTES", "30")) * 60
INTERACTIVE_MAX_AGE_SECS = int(os.environ.get("INTERACTIVE_MAX_AGE_HOURS", "2")) * 3600
VAULT_REPO = os.environ.get("VAULT_REPO", "")
VAULT_PATH = "/vault"
REFLECTION_MEMORY_PATH = os.path.join(VAULT_PATH, "Bede", "reflection-memory.md")

_scheduler: AsyncIOScheduler | None = None

# {chat_id: {"session_id": str, "ts": float}}
_sessions: dict[int, dict] = {}

# Single interactive task session: {"session_id": str, "model": str, "ts": float, "created": float}
_interactive_session: dict | None = None

REAUTH_NOTICE = (
    "\u26a0\ufe0f Claude auth has expired.\n\n"
    "Run this from your Mac to re-authenticate:\n"
    "```\n"
    'security find-generic-password -s "Claude Code-credentials" -w | \\\n'
    '  ssh user@SERVER_IP "cat > ~/.claude/.credentials.json"\n'
    "```"
)


def _build_cmd(text: str, session_id: str | None, model: str | None = None) -> list[str]:
    cmd = [
        "claude", "-p", text,
        "--model", model or CLAUDE_MODEL,
        "--dangerously-skip-permissions",
        "--output-format", "json",
    ]
    if session_id:
        cmd += ["--resume", session_id]
    return cmd


def _pull_vault():
    """Pull latest vault state before invoking Claude. Fails silently."""
    if not VAULT_REPO or not os.path.isdir("/vault/.git"):
        return
    try:
        subprocess.run(
            ["git", "-C", "/vault", "pull", "--ff-only"],
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass


def register_interactive_session(session_id: str, model: str):
    """Called by scheduler (via call_soon_threadsafe) to hand off an interactive task session."""
    global _interactive_session
    now = time.monotonic()
    _interactive_session = {
        "session_id": session_id,
        "model": model,
        "ts": now,
        "created": now,
    }
    log.info("Interactive session registered: %s (model: %s)", session_id, model)


def _get_interactive_session(now: float) -> dict | None:
    """Return the active interactive session if within both idle and max-age limits."""
    global _interactive_session
    if _interactive_session is None:
        return None
    idle_ok = (now - _interactive_session["ts"]) < INTERACTIVE_IDLE_TIMEOUT_SECS
    age_ok = (now - _interactive_session["created"]) < INTERACTIVE_MAX_AGE_SECS
    if idle_ok and age_ok:
        return _interactive_session
    log.info("Interactive session expired (idle_ok=%s, age_ok=%s).", idle_ok, age_ok)
    _interactive_session = None
    return None


def _append_correction(text: str):
    """Append a timestamped correction to reflection-memory.md. Creates the file if missing."""
    from datetime import datetime
    from zoneinfo import ZoneInfo
    tz_name = os.environ.get("TIMEZONE", "UTC")
    now = datetime.now(ZoneInfo(tz_name))
    timestamp = now.strftime("%Y-%m-%d %H:%M")

    header = (
        "# Reflection Memory\n\n"
        "Corrections and preferences Joe has provided about Evening Reflections.\n"
        "Bede reads this at the start of each reflection to avoid repeating mistakes.\n\n"
        "## Corrections\n\n"
    )

    if not os.path.isfile(REFLECTION_MEMORY_PATH):
        os.makedirs(os.path.dirname(REFLECTION_MEMORY_PATH), exist_ok=True)
        with open(REFLECTION_MEMORY_PATH, "w") as f:
            f.write(header)

    with open(REFLECTION_MEMORY_PATH, "a") as f:
        f.write(f"- [{timestamp}] {text}\n")

    try:
        subprocess.run(
            ["git", "-C", VAULT_PATH, "add", REFLECTION_MEMORY_PATH],
            capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "-C", VAULT_PATH, "commit", "-m", "reflection: save correction"],
            capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "-C", VAULT_PATH, "push"],
            capture_output=True, timeout=30,
        )
    except Exception as e:
        log.warning("Failed to commit reflection correction: %s", e)


def _parse_output(stdout: str) -> tuple[str, str | None]:
    """
    claude --output-format json emits newline-delimited JSON objects.
    The final object with type=result contains the answer and session_id.
    """
    result_text = ""
    session_id = None

    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        if obj.get("type") == "result":
            result_text = obj.get("result", "").strip()
            session_id = obj.get("session_id")

    return result_text, session_id


CLAUDE_TIMEOUT = 120

def _run_claude(cmd: list[str], workdir: str) -> subprocess.CompletedProcess:
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, cwd=workdir, text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(timeout=CLAUDE_TIMEOUT)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            proc.kill()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            pass
        raise


TYPING_MAX_DURATION = 600

async def _keep_typing(bot, chat_id: int, max_duration: float = TYPING_MAX_DURATION):
    """Sends typing action every 4s. Auto-stops after max_duration as a safety net."""
    deadline = time.monotonic() + max_duration
    while time.monotonic() < deadline:
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
        except Exception:
            pass
        await asyncio.sleep(4)
    log.warning("Typing indicator exceeded %ds safety limit.", int(max_duration))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _interactive_session
    if update.effective_user.id != ALLOWED_USER_ID:
        log.warning("Rejected message from user %s", update.effective_user.id)
        return

    chat_id = update.effective_chat.id
    text = update.message.text
    now = time.monotonic()

    # Check interactive task session first, then regular chat session
    interactive = _get_interactive_session(now)
    if interactive:
        resume_id = interactive["session_id"]
        model = interactive.get("model")
    else:
        session = _sessions.get(chat_id)
        resume_id = None
        model = None
        if session and (now - session["ts"]) < SESSION_TIMEOUT_SECS:
            resume_id = session["session_id"]

    reset_sent = False
    await asyncio.to_thread(_pull_vault)

    cmd = _build_cmd(text, resume_id, model=model)
    log.info("Running: %s", " ".join(cmd[:4]) + " ...")

    typing_task = asyncio.create_task(_keep_typing(context.bot, chat_id))
    try:
        proc = await asyncio.to_thread(_run_claude, cmd, CLAUDE_WORKDIR)
    except subprocess.TimeoutExpired:
        typing_task.cancel()
        await update.message.reply_text("Request timed out after 2 minutes.")
        return
    finally:
        typing_task.cancel()

    # Stale session detection — retry once with a fresh session
    if resume_id and "no conversation found" in proc.stderr.lower():
        log.warning("Stale session %s, retrying fresh.", resume_id)
        _sessions.pop(chat_id, None)
        if interactive:
            _interactive_session = None
            interactive = None
        await update.message.reply_text("_(Session reset — previous context lost)_", parse_mode="Markdown")
        reset_sent = True
        cmd = _build_cmd(text, None)
        typing_task = asyncio.create_task(_keep_typing(context.bot, chat_id))
        try:
            proc = await asyncio.to_thread(_run_claude, cmd, CLAUDE_WORKDIR)
        except subprocess.TimeoutExpired:
            typing_task.cancel()
            await update.message.reply_text("Request timed out after 2 minutes.")
            return
        finally:
            typing_task.cancel()

    # Auth failure detection
    stderr_lower = proc.stderr.lower()
    if proc.returncode != 0 and any(
        kw in stderr_lower for kw in ("unauthorized", "authentication", "auth", "login")
    ):
        log.error("Auth failure detected: %s", proc.stderr[:200])
        await update.message.reply_text(REAUTH_NOTICE, parse_mode="Markdown")
        return

    result_text, new_session_id = _parse_output(proc.stdout)

    if not result_text:
        # Fallback: surface raw output so failures are visible
        result_text = (proc.stdout or proc.stderr or "No response.").strip()[:4096]

    # Update session state
    if interactive and new_session_id:
        _interactive_session["session_id"] = new_session_id
        _interactive_session["ts"] = now
        await asyncio.to_thread(_append_correction, text)
    elif interactive and not new_session_id:
        _interactive_session = None
        log.info("Interactive session ended (no session_id returned).")
    elif new_session_id:
        _sessions[chat_id] = {"session_id": new_session_id, "ts": now}
        if not resume_id and not reset_sent:
            await update.message.reply_text("_(New context started)_", parse_mode="Markdown")
    else:
        if _sessions.pop(chat_id, None):
            await update.message.reply_text("_(Session reset — previous context lost)_", parse_mode="Markdown")

    # Telegram message limit is 4096 chars; convert markdown to HTML, fall back to plain text
    for chunk in [result_text[i:i + 4096] for i in range(0, len(result_text), 4096)]:
        try:
            await update.message.reply_text(md_to_html(chunk), parse_mode="HTML")
        except Exception:
            await update.message.reply_text(chunk)


async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _interactive_session
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    chat_id = update.effective_chat.id
    _sessions.pop(chat_id, None)
    _interactive_session = None
    cancelled = cancel_all_tasks()
    if cancelled:
        names = ", ".join(cancelled)
        await update.message.reply_text(f"Session cleared. Cancelled running tasks: {names}")
    else:
        await update.message.reply_text("Session cleared. Next message starts fresh.")


async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    await update.message.reply_text(
        "Hi, I'm Bede. Send me a message to get started.\n"
        "/reset — start a new conversation session"
    )


async def _safe_reply(message, text: str):
    try:
        await message.reply_text(text)
    except Exception as e:
        log.warning("Failed to send Telegram reply (%s): %s", text, e)


async def _trigger_task(update: Update, task_name: str):
    """Look up a task by name and run it in the background."""
    if update.effective_user.id != ALLOWED_USER_ID:
        return
    if task_name in _running_tasks:
        await _safe_reply(update.message, f"⚠️ {task_name} is already running.")
        return
    tasks = _parse_tasks()
    task = next((t for t in tasks if t.get("name") == task_name), None)
    if not task:
        await _safe_reply(update.message, f"{task_name} not found in scheduled-tasks.md.")
        return
    await _safe_reply(update.message, f"Running {task_name}...")
    asyncio.create_task(_run_task(task))


async def handle_scout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _trigger_task(update, "Deal Scout")


async def handle_morning(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _trigger_task(update, "Morning Briefing")


async def handle_evening(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _trigger_task(update, "Evening Reflection")


async def handle_datacheck(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _trigger_task(update, "Evening Data Check")


async def handle_triage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _trigger_task(update, "Email Triage")


async def post_init(app):
    from telegram import BotCommand, BotCommandScopeAllPrivateChats
    commands = [
        BotCommand("start", "Start a conversation"),
        BotCommand("reset", "Clear session and start fresh"),
        BotCommand("morning", "Run the Morning Briefing"),
        BotCommand("evening", "Run the Evening Reflection"),
        BotCommand("scout", "Run the Deal Scout"),
        BotCommand("datacheck", "Run the Evening Data Check"),
        BotCommand("triage", "Triage today's emails for tasks and events"),
    ]
    await app.bot.set_my_commands(commands)
    await app.bot.set_my_commands(commands, scope=BotCommandScopeAllPrivateChats())

    global _scheduler
    _scheduler = setup_scheduler(app.bot, ALLOWED_USER_ID)
    _scheduler.start()
    await scheduler_reload(_scheduler)
    log.info("Scheduler started.")


async def post_shutdown(app):
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        log.info("Scheduler stopped.")


def main():
    app = Application.builder().token(BOT_TOKEN).post_init(post_init).post_shutdown(post_shutdown).build()
    app.add_handler(CommandHandler("start", handle_start))
    app.add_handler(CommandHandler("reset", handle_reset))
    app.add_handler(CommandHandler("morning", handle_morning))
    app.add_handler(CommandHandler("evening", handle_evening))
    app.add_handler(CommandHandler("scout", handle_scout))
    app.add_handler(CommandHandler("datacheck", handle_datacheck))
    app.add_handler(CommandHandler("triage", handle_triage))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    log.info("Bede is running.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    import sys
    sys.modules["bot"] = sys.modules[__name__]
    main()
