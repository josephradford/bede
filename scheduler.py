"""
Scheduled task runner for Bede.

Reads task definitions from YAML frontmatter in a markdown file inside the
Obsidian vault (BEDE_TASKS_PATH, relative to /vault). Reloads every 5 minutes
to pick up edits made in Obsidian without restarting the container.

Task file format (YAML frontmatter):

    ---
    tasks:
      - name: Morning Briefing
        schedule: "0 7 * * 1-5"   # standard 5-field cron, evaluated in TIMEZONE
        prompt: |
          Give me a morning briefing: today's calendar events and the weather.
      - name: Weekly Review
        schedule: "0 16 * * 5"
        prompt: "Remind me to do my weekly review."
        enabled: false             # set false to skip without deleting
    ---
"""

import asyncio
import json
import logging
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from utils import md_to_html

log = logging.getLogger(__name__)

VAULT_PATH = "/vault"
TASKS_REL_PATH = os.environ.get("BEDE_TASKS_PATH", "Bede/scheduled-tasks.md")
TIMEZONE = os.environ.get("TIMEZONE", "UTC")
CLAUDE_WORKDIR = os.environ.get("CLAUDE_WORKDIR", "/app")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
RELOAD_INTERVAL_MINUTES = 5

_bot = None
_chat_id: int = 0


def _pull_vault():
    """Pull latest vault state. Fails silently."""
    if not os.path.isdir(os.path.join(VAULT_PATH, ".git")):
        return
    try:
        subprocess.run(
            ["git", "-C", VAULT_PATH, "pull", "--ff-only"],
            capture_output=True,
            timeout=30,
        )
    except Exception:
        pass


def _parse_tasks() -> list[dict]:
    """Read and parse a ```yaml code block from the tasks file in the vault."""
    full_path = os.path.join(VAULT_PATH, TASKS_REL_PATH)
    if not os.path.isfile(full_path):
        log.debug("Tasks file not found at %s — no scheduled tasks.", full_path)
        return []

    with open(full_path) as f:
        content = f.read()

    # Extract content between first ```yaml ... ``` block
    import re
    match = re.search(r"```yaml\s*\n(.*?)```", content, re.DOTALL)
    if not match:
        log.warning("Tasks file has no ```yaml code block: %s", full_path)
        return []

    try:
        data = yaml.safe_load(match.group(1)) or {}
        tasks = data.get("tasks", [])
        enabled = [t for t in tasks if t.get("enabled", True)]
        valid = []
        for t in enabled:
            if t.get("interactive") and t.get("steps"):
                log.error("Task '%s': interactive + steps is not supported — skipping.", t.get("name"))
                continue
            valid.append(t)
        log.info("Loaded %d scheduled task(s) from vault.", len(valid))
        return valid
    except yaml.YAMLError as e:
        log.error("Failed to parse tasks YAML: %s", e)
        return []


async def _send(text: str):
    """Send a message to the user's Telegram chat."""
    try:
        await _bot.send_message(
            chat_id=_chat_id,
            text=md_to_html(text),
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except Exception as e:
        log.error("Failed to send scheduled message: %s", e)


TYPING_MAX_DURATION = 3600

async def _keep_typing(max_duration: float = TYPING_MAX_DURATION):
    """Send typing action every 4s. Auto-stops after max_duration as a safety net."""
    deadline = time.monotonic() + max_duration
    while time.monotonic() < deadline:
        try:
            await _bot.send_chat_action(chat_id=_chat_id, action="typing")
        except Exception:
            pass
        await asyncio.sleep(4)
    log.warning("Typing indicator exceeded %ds safety limit.", int(max_duration))


DEFAULT_TASK_TIMEOUT = 300  # seconds

_running_tasks: dict[str, asyncio.Task] = {}
_running_procs: dict[str, subprocess.Popen] = {}


def cancel_all_tasks() -> list[str]:
    """Cancel all running tasks and kill their subprocesses. Returns cancelled task names."""
    cancelled = []
    for name, proc in list(_running_procs.items()):
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
    _running_procs.clear()
    for name, task in list(_running_tasks.items()):
        task.cancel()
        cancelled.append(name)
    return cancelled

_task_env = None


def _get_task_env() -> dict:
    global _task_env
    if _task_env is None:
        _task_env = {k: v for k, v in os.environ.items()
                     if k not in ("TELEGRAM_BOT_TOKEN", "ALLOWED_USER_ID")}
    return _task_env


async def _run_subprocess(cmd: list[str], timeout: int, task_name: str) -> subprocess.CompletedProcess:
    """Run a subprocess with tracking for cancellation. Raises TimeoutExpired or CancelledError."""
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        stdin=subprocess.DEVNULL, cwd=CLAUDE_WORKDIR,
        text=True, env=_get_task_env(), start_new_session=True,
    )
    _running_procs[task_name] = proc
    try:
        stdout, stderr = await asyncio.to_thread(proc.communicate, timeout=timeout)
        return subprocess.CompletedProcess(cmd, proc.returncode, stdout, stderr)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except (ProcessLookupError, OSError):
            pass
        try:
            await asyncio.to_thread(proc.wait, 10)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except (ProcessLookupError, OSError):
                proc.kill()
            try:
                await asyncio.to_thread(proc.wait, 5)
            except subprocess.TimeoutExpired:
                pass
        raise
    finally:
        _running_procs.pop(task_name, None)


def _extract_session_id(stdout: str) -> str | None:
    """Extract just the session_id from claude JSON output."""
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("type") == "result":
                return obj.get("session_id")
        except json.JSONDecodeError:
            continue
    return None


def _extract_result(stdout: str) -> str:
    """Extract the result text from claude --output-format json output."""
    result_text = ""
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if obj.get("type") == "result":
                result_text = obj.get("result", "").strip()
        except json.JSONDecodeError:
            continue
    return result_text


async def _run_task(task: dict):
    """Run a single scheduled task and send the result via Telegram."""
    name = task.get("name", "Scheduled Task")

    if name in _running_tasks:
        log.warning("Task '%s' is already running — skipping.", name)
        await _send(f"⚠️ *{name}* is already running.")
        return

    _running_tasks[name] = asyncio.current_task()
    await asyncio.to_thread(_pull_vault)
    timeout = int(task.get("timeout", DEFAULT_TASK_TIMEOUT))
    steps = task.get("steps")
    max_typing = (timeout * len(steps) + 120) if steps else (timeout + 120)
    typing_task = asyncio.create_task(_keep_typing(max_duration=max_typing))
    try:
        await _run_task_inner(task, name)
    except asyncio.CancelledError:
        log.info("Task '%s' was cancelled.", name)
        try:
            await _send(f"🛑 *{name}* cancelled.")
        except Exception:
            pass
    finally:
        typing_task.cancel()
        _running_tasks.pop(name, None)


async def _run_task_inner(task: dict, name: str):
    steps = task.get("steps")
    if steps:
        await _run_steps_task(task, name, steps)
        return

    prompt = task.get("prompt", "")
    timeout = int(task.get("timeout", DEFAULT_TASK_TIMEOUT))
    model = task.get("model", CLAUDE_MODEL)
    cron = task.get("schedule", "")

    log.info("Running scheduled task: %s (timeout: %ds, model: %s)", name, timeout, model)

    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    now_str = now.strftime("%H:%M")
    now_date_str = now.strftime("%A, %d %B %Y")
    prompt = f"Today is {now_date_str}.\n\n{prompt}"

    next_str = _next_run_str(cron, tz, now)

    header = f"📅 *{name}* ({now_str})"
    if next_str:
        header += f"\n↻ Next: {next_str}"
    header += "\n---\n"

    cmd = [
        "claude", "-p", prompt,
        "--model", model,
        "--dangerously-skip-permissions",
        "--output-format", "json",
    ]

    try:
        proc = await _run_subprocess(cmd, timeout, name)
    except subprocess.TimeoutExpired:
        mins = timeout // 60
        await _send(f"📅 *{name}*\n⚠️ Timed out after {mins} minutes.")
        return
    except Exception as e:
        await _send(f"📅 *{name}*\n⚠️ Error: {e}")
        return

    result_text = _extract_result(proc.stdout)

    if not result_text:
        if proc.returncode != 0:
            result_text = f"⚠️ Task failed (exit {proc.returncode}):\n{(proc.stderr or proc.stdout or 'No output.')[:500]}"
        else:
            result_text = (proc.stdout or proc.stderr or "No response.").strip()

    full = header + result_text
    for chunk in [full[i:i + 4096] for i in range(0, len(full), 4096)]:
        await _send(chunk)

    if task.get("interactive"):
        session_id = _extract_session_id(proc.stdout)
        if session_id:
            import bot as _bot_module
            _bot_module.register_interactive_session(session_id, model)
            log.info("Interactive session handed off for task '%s': %s", name, session_id)
        else:
            log.warning("Task '%s' is interactive but no session_id was returned.", name)


def _next_run_str(cron: str, tz, now) -> str:
    if not cron:
        return ""
    try:
        trigger = CronTrigger.from_crontab(cron, timezone=tz)
        next_run = trigger.get_next_fire_time(None, now)
        if next_run:
            return next_run.strftime("%a %H:%M")
    except Exception as e:
        log.warning("Could not calculate next run time: %s", e)
    return ""


_NOTES_SEPARATOR = "---NOTES---"

_PARALLEL_NOTE = (
    "\n\nIMPORTANT: You are running in parallel with other scout categories. "
    "Do NOT write to or modify /vault/Bede/price-checker-memory.md. "
    "Instead, put any dead URLs, price changes, or stock transitions "
    f"AFTER a `{_NOTES_SEPARATOR}` separator line at the end of your response. "
    "Content before the separator goes to Telegram. Content after it is "
    "internal-only and will be collected by the Update Memory step."
)


async def _run_single_step(step: dict, task_name: str, model: str, preamble: str,
                           now_date_str: str, step_timeout: int) -> tuple[str, str, bool]:
    """Run one step of a multi-step task. Returns (step_name, result_text, silent)."""
    step_name = step.get("name", "Step")
    step_prompt = step.get("prompt", "")
    silent = step.get("silent", False)
    step_model = step.get("model", model)

    if not step_prompt:
        return step_name, "", silent

    full_prompt = f"Today is {now_date_str}.\n\n"
    if preamble:
        full_prompt += preamble + "\n\n"
    full_prompt += step_prompt

    cmd = [
        "claude", "-p", full_prompt,
        "--model", step_model,
        "--dangerously-skip-permissions",
        "--output-format", "json",
    ]

    log.info("Running step '%s' for task '%s'", step_name, task_name)
    proc_key = f"{task_name}/{step_name}"

    try:
        proc = await _run_subprocess(cmd, step_timeout, proc_key)
    except subprocess.TimeoutExpired:
        return step_name, f"⚠️ *{step_name}* — timed out", silent
    except Exception as e:
        return step_name, f"⚠️ *{step_name}* — error: {e}", silent

    result_text = _extract_result(proc.stdout)

    if not result_text:
        if proc.returncode != 0:
            result_text = f"⚠️ Failed (exit {proc.returncode}):\n{(proc.stderr or proc.stdout or 'No output.')[:500]}"
        else:
            result_text = (proc.stdout or proc.stderr or "No output.").strip()

    return step_name, result_text, silent


async def _run_steps_task(task: dict, name: str, steps: list[dict]):
    """Run a multi-step task, optionally parallelizing non-silent steps."""
    timeout = int(task.get("timeout", DEFAULT_TASK_TIMEOUT))
    model = task.get("model", CLAUDE_MODEL)
    cron = task.get("schedule", "")
    preamble = task.get("preamble", "")
    parallel = task.get("parallel", False)

    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    now_str = now.strftime("%H:%M")
    now_date_str = now.strftime("%A, %d %B %Y")
    next_str = _next_run_str(cron, tz, now)

    header = f"📅 *{name}* ({now_str})"
    if next_str:
        header += f"\n↻ Next: {next_str}"
    step_names = [s.get("name", f"Step {i+1}") for i, s in enumerate(steps) if not s.get("silent")]
    header += f"\n{len(step_names)} sections: {', '.join(step_names)}"
    if parallel:
        header += " ⚡"
    await _send(header)

    if parallel:
        await _run_steps_parallel(steps, name, timeout, model, preamble, now_date_str)
    else:
        step_timeout = max(timeout // len(steps), 120)
        for step in steps:
            step_name, result_text, silent = await _run_single_step(
                step, name, model, preamble, now_date_str, step_timeout,
            )
            if not silent and result_text:
                for chunk in [result_text[j:j + 4096] for j in range(0, len(result_text), 4096)]:
                    await _send(chunk)
            elif silent:
                log.info("Silent step '%s' completed.", step_name)

    await _send(f"✅ *{name}* complete.")


async def _run_steps_parallel(steps: list[dict], task_name: str, timeout: int,
                              model: str, preamble: str, now_date_str: str):
    """Run non-silent steps concurrently, then silent steps sequentially with collected results."""
    parallel_steps = [s for s in steps if not s.get("silent")]
    sequential_steps = [s for s in steps if s.get("silent")]

    parallel_preamble = (preamble + _PARALLEL_NOTE) if preamble else ""

    async def _run_and_send(step: dict) -> tuple[str, str]:
        step_name, result_text, _ = await _run_single_step(
            step, task_name, model, parallel_preamble, now_date_str, timeout,
        )
        if result_text:
            visible = result_text.split(_NOTES_SEPARATOR, 1)[0].rstrip()
            if visible:
                for chunk in [visible[j:j + 4096] for j in range(0, len(visible), 4096)]:
                    await _send(chunk)
        return step_name, result_text

    results = await asyncio.gather(
        *(_run_and_send(s) for s in parallel_steps),
        return_exceptions=True,
    )

    collected = []
    for r in results:
        if isinstance(r, Exception):
            log.error("Parallel step failed: %s", r)
        else:
            collected.append(r)

    if sequential_steps:
        context = "\n\n".join(f"## {sn}\n{st}" for sn, st in collected if st)
        seq_preamble = preamble
        if context:
            seq_preamble += f"\n\nResults from parallel steps:\n\n{context}"

        step_timeout = max(timeout // len(sequential_steps), 120)
        for step in sequential_steps:
            step_name, result_text, silent = await _run_single_step(
                step, task_name, model, seq_preamble, now_date_str, step_timeout,
            )
            if not silent and result_text:
                for chunk in [result_text[j:j + 4096] for j in range(0, len(result_text), 4096)]:
                    await _send(chunk)
            else:
                log.info("Silent step '%s' completed.", step_name)


async def reload(scheduler: AsyncIOScheduler):
    """Pull vault, re-parse tasks, and rebuild scheduled jobs."""
    await asyncio.to_thread(_pull_vault)
    tasks = _parse_tasks()

    # Remove vault-defined task jobs; keep built-in jobs (reload_watcher, collect_bede_sessions)
    _builtin_jobs = {"reload_watcher", "collect_bede_sessions"}
    for job in scheduler.get_jobs():
        if job.id not in _builtin_jobs:
            job.remove()

    tz = ZoneInfo(TIMEZONE)
    for task in tasks:
        cron = task.get("schedule", "")
        name = task.get("name", "task")
        if not cron:
            log.warning("Task '%s' has no schedule — skipping.", name)
            continue
        try:
            scheduler.add_job(
                _run_task,
                CronTrigger.from_crontab(cron, timezone=tz),
                args=[task],
                id=f"task_{name}",
                name=name,
                replace_existing=True,
            )
            log.info("Scheduled '%s' with cron '%s' (%s)", name, cron, TIMEZONE)
        except Exception as e:
            log.error("Invalid schedule for '%s': %s", name, e)


async def _collect_sessions_job():
    """Built-in nightly job: collect and POST Bede session summaries."""
    from collect_sessions import collect_and_post
    try:
        await asyncio.to_thread(collect_and_post)
    except Exception as e:
        log.error("Session collection failed: %s", e)


def setup_scheduler(bot, chat_id: int) -> AsyncIOScheduler:
    """Create and configure the scheduler. Call start() and await reload() after."""
    global _bot, _chat_id
    _bot = bot
    _chat_id = chat_id

    tz = ZoneInfo(TIMEZONE)

    scheduler = AsyncIOScheduler(
        job_defaults={"misfire_grace_time": 300, "coalesce": True}
    )
    scheduler.add_job(
        reload,
        "interval",
        minutes=RELOAD_INTERVAL_MINUTES,
        args=[scheduler],
        id="reload_watcher",
        name="Task reload watcher",
    )
    scheduler.add_job(
        _collect_sessions_job,
        CronTrigger(hour=2, minute=0, timezone=tz),
        id="collect_bede_sessions",
        name="Collect Bede session summaries",
        replace_existing=True,
    )
    log.info("Built-in job: collect_bede_sessions scheduled at 02:00 %s", TIMEZONE)
    return scheduler
