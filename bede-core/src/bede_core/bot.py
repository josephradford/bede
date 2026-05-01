import asyncio
import logging
import time

from telegram import Update
from telegram.ext import ContextTypes

from bede_core.session_manager import SessionManager
from bede_core.telegram_format import md_to_html, chunk_text

log = logging.getLogger(__name__)

REAUTH_NOTICE = (
    "⚠️ Claude auth has expired.\n\n"
    "Run this from your Mac to re-authenticate:\n"
    "```\n"
    'security find-generic-password -s "Claude Code-credentials" -w | \\\n'
    '  ssh user@SERVER_IP "cat > ~/.claude/.credentials.json"\n'
    "```"
)

TYPING_MAX_DURATION = 600


async def _keep_typing(bot, chat_id: int, max_duration: float = TYPING_MAX_DURATION):
    deadline = time.monotonic() + max_duration
    while time.monotonic() < deadline:
        try:
            await bot.send_chat_action(chat_id=chat_id, action="typing")
        except Exception:
            pass
        await asyncio.sleep(4)


async def _send_response(message, text: str):
    for c in chunk_text(text):
        try:
            await message.reply_text(
                md_to_html(c), parse_mode="HTML", disable_web_page_preview=True
            )
        except Exception:
            await message.reply_text(c, disable_web_page_preview=True)


def create_message_handler(
    session_manager: SessionManager,
    allowed_user_id: int,
    timezone: str,
    data_client=None,
    append_correction_fn=None,
):
    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != allowed_user_id:
            log.warning("Rejected message from user %s", update.effective_user.id)
            return

        chat_id = update.effective_chat.id
        text = update.message.text

        typing_task = asyncio.create_task(_keep_typing(context.bot, chat_id))
        try:
            result = await session_manager.send(text)
        except Exception as e:
            log.error("Unexpected error handling message: %s", e)
            await update.message.reply_text("Something went wrong. Please try again.")
            return
        finally:
            typing_task.cancel()

        if result.timed_out:
            if data_client:
                await data_client.post(
                    "/api/message-queue", body={"message": text, "source": "telegram"}
                )
                await update.message.reply_text(
                    "Request timed out. I've queued your message and will process it when I'm available."
                )
            else:
                await update.message.reply_text("Request timed out.")
            return

        if result.auth_failure:
            if data_client:
                await data_client.post(
                    "/api/message-queue", body={"message": text, "source": "telegram"}
                )
            await update.message.reply_text(REAUTH_NOTICE, parse_mode="Markdown")
            return

        response_text = result.text or "No response."

        if result.stop_reason == "max_tokens":
            response_text += (
                "\n\n⚠️ _Response was truncated (output token limit reached)._"
            )

        if session_manager.is_interactive and append_correction_fn:
            await asyncio.to_thread(append_correction_fn, text)

        await _send_response(update.message, response_text)

    return handle_message


def create_reset_handler(session_manager: SessionManager, allowed_user_id: int, runner=None):
    async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != allowed_user_id:
            return
        await session_manager.clear_daily_session()
        session_manager.clear_interactive()
        cancelled = runner.cancel_all() if runner else []
        if cancelled:
            names = ", ".join(cancelled)
            await update.message.reply_text(f"Session cleared. Cancelled running tasks: {names}")
        else:
            await update.message.reply_text("Session cleared. Next message starts fresh.")

    return handle_reset


def create_start_handler(allowed_user_id: int):
    async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != allowed_user_id:
            return
        await update.message.reply_text(
            "Hi, I'm Bede. Send me a message to get started.\n"
            "/reset — start a new conversation session"
        )

    return handle_start


def create_task_trigger_handler(
    task_name: str,
    runner,
    data_client,
    allowed_user_id: int,
):
    async def handle_trigger(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != allowed_user_id:
            return

        if runner.is_running(task_name):
            await update.message.reply_text(f"⚠️ {task_name} is already running.")
            return

        schedules = await data_client.get("/api/config/schedules")
        all_schedules = schedules.get("schedules", [])
        task = next((s for s in all_schedules if s.get("task_name") == task_name), None)

        if not task:
            await update.message.reply_text(f"{task_name} not found in schedules.")
            return

        await update.message.reply_text(f"Running {task_name}...")
        asyncio.create_task(runner.run_task(task))

    return handle_trigger
