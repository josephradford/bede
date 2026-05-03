import asyncio
import logging
import time
from functools import partial

from telegram import BotCommand, BotCommandScopeAllPrivateChats
from telegram.ext import Application, CommandHandler, MessageHandler, filters

from bede_core.bot import (
    create_message_handler,
    create_reset_handler,
    create_start_handler,
    create_task_trigger_handler,
)
from bede_core.claude_cli import ClaudeCli
from bede_core.config import Settings
from bede_core.data_client import DataClient
from bede_core.memory_manager import MemoryManager
from bede_core.reflection import append_correction
from bede_core.scheduler import TaskRunner, reload_schedules, setup_scheduler
from bede_core.session_manager import SessionManager
from bede_core.telegram_format import md_to_html, chunk_text

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)


def _start_health_server(port: int = 8080):
    """Minimal HTTP health endpoint on a background thread."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import threading

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"ok")
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass

    server = HTTPServer(("0.0.0.0", port), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()


log = logging.getLogger(__name__)


def main():
    settings = Settings()
    _start_health_server()

    data_client = DataClient(base_url=settings.bede_data_url)

    claude_cli = ClaudeCli(
        workdir=settings.claude_workdir,
        timeout=settings.claude_timeout_seconds,
        filter_env_keys=["TELEGRAM_BOT_TOKEN", "ALLOWED_USER_ID", "INGEST_WRITE_TOKEN"],
        mcp_config=settings.mcp_config_path,
    )

    memory_manager = MemoryManager(data_client)

    session_manager = SessionManager(
        data_client=data_client,
        claude_cli=claude_cli,
        memory_manager=memory_manager,
        timezone=settings.timezone,
        model=settings.claude_model,
        vault_path=settings.vault_path,
        interactive_idle_timeout=settings.interactive_idle_timeout_minutes * 60,
        interactive_max_age=settings.interactive_max_age_hours * 3600,
    )

    async def send_telegram(text: str):
        for c in chunk_text(text):
            try:
                await app.bot.send_message(
                    chat_id=settings.allowed_user_id,
                    text=md_to_html(c),
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                )
            except Exception:
                try:
                    await app.bot.send_message(
                        chat_id=settings.allowed_user_id,
                        text=c,
                        disable_web_page_preview=True,
                    )
                except Exception as e:
                    log.error("Failed to send Telegram message: %s", e)

    correction_fn = partial(
        append_correction,
        vault_path=settings.vault_path,
        timezone=settings.timezone,
    )

    async def keep_typing():
        deadline = time.monotonic() + 3600
        while time.monotonic() < deadline:
            try:
                await app.bot.send_chat_action(
                    chat_id=settings.allowed_user_id, action="typing"
                )
            except Exception:
                pass
            await asyncio.sleep(4)

    runner = TaskRunner(
        data_client=data_client,
        session_manager=session_manager,
        send_fn=send_telegram,
        timezone=settings.timezone,
        quiet_hours_start=settings.quiet_hours_start,
        quiet_hours_end=settings.quiet_hours_end,
        typing_fn=keep_typing,
    )

    scheduler = setup_scheduler(data_client, runner, settings.timezone)

    async def post_init(application):
        commands = [
            BotCommand("start", "Start a conversation"),
            BotCommand("reset", "Clear session and start fresh"),
            BotCommand("morning", "Run the Morning Briefing"),
            BotCommand("evening", "Run the Evening Reflection"),
            BotCommand("scout", "Run the Deal Scout"),
            BotCommand("datacheck", "Run the Evening Data Check"),
            BotCommand("triage", "Triage today's emails"),
        ]
        await application.bot.set_my_commands(commands)
        await application.bot.set_my_commands(
            commands, scope=BotCommandScopeAllPrivateChats()
        )

        scheduler.start()
        await reload_schedules(scheduler, data_client, runner, settings.timezone)
        log.info("Scheduler started.")

    async def post_shutdown(application):
        if scheduler.running:
            scheduler.shutdown(wait=False)
            log.info("Scheduler stopped.")

    app = (
        Application.builder()
        .token(settings.telegram_bot_token)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    app.add_handler(
        CommandHandler("start", create_start_handler(settings.allowed_user_id))
    )
    app.add_handler(
        CommandHandler(
            "reset",
            create_reset_handler(
                session_manager, settings.allowed_user_id, runner=runner
            ),
        )
    )
    app.add_handler(
        CommandHandler(
            "morning",
            create_task_trigger_handler(
                "Morning Briefing", runner, data_client, settings.allowed_user_id
            ),
        )
    )
    app.add_handler(
        CommandHandler(
            "evening",
            create_task_trigger_handler(
                "Evening Reflection", runner, data_client, settings.allowed_user_id
            ),
        )
    )
    app.add_handler(
        CommandHandler(
            "scout",
            create_task_trigger_handler(
                "Deal Scout", runner, data_client, settings.allowed_user_id
            ),
        )
    )
    app.add_handler(
        CommandHandler(
            "datacheck",
            create_task_trigger_handler(
                "Evening Data Check", runner, data_client, settings.allowed_user_id
            ),
        )
    )
    app.add_handler(
        CommandHandler(
            "triage",
            create_task_trigger_handler(
                "Email Triage", runner, data_client, settings.allowed_user_id
            ),
        )
    )
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            create_message_handler(
                session_manager,
                settings.allowed_user_id,
                settings.timezone,
                data_client=data_client,
                append_correction_fn=correction_fn,
            ),
        )
    )

    log.info("Bede is running.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
