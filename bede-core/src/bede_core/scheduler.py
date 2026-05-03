import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from bede_core.data_client import DataClient
from bede_core.quiet_hours import is_quiet_hours
from bede_core.session_manager import SessionManager

log = logging.getLogger(__name__)

RELOAD_INTERVAL_MINUTES = 5


async def load_schedules(data_client: DataClient) -> list[dict]:
    result = await data_client.get("/api/config/schedules")
    if "error" in result:
        log.warning("Failed to load schedules: %s", result["error"])
        return []
    schedules = result.get("schedules", [])
    return [s for s in schedules if s.get("enabled", True)]


class TaskRunner:
    def __init__(
        self,
        data_client: DataClient,
        session_manager: SessionManager,
        send_fn,
        timezone: str,
        quiet_hours_start: int = 22,
        quiet_hours_end: int = 7,
        typing_fn=None,
    ):
        self._data = data_client
        self._session = session_manager
        self._send = send_fn
        self._tz = ZoneInfo(timezone)
        self._running: set[str] = set()
        self._quiet_start = quiet_hours_start
        self._quiet_end = quiet_hours_end
        self._typing_fn = typing_fn

    async def _log_start(self, task_name: str) -> int | None:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        result = await self._data.post(
            "/api/tasks/log",
            body={
                "task_name": task_name,
                "start_time": now,
                "status": "running",
            },
        )
        return result.get("id")

    async def _log_end(
        self,
        exec_id: int | None,
        status: str,
        duration: float,
        error: str | None = None,
    ):
        if exec_id is None:
            return
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        body: dict = {"status": status, "end_time": now, "duration_seconds": duration}
        if error:
            body["error_detail"] = error[:1000]
        await self._data.put(f"/api/tasks/log/{exec_id}", body=body)

    async def run_task(self, task: dict):
        name = task["task_name"]

        if name in self._running:
            log.warning("Task '%s' already running — skipping.", name)
            return

        self._running.add(name)
        start = time.monotonic()
        exec_id = await self._log_start(name)

        typing_task = None
        if self._typing_fn:
            typing_task = asyncio.create_task(self._typing_fn())

        try:
            await self._run_task_inner(task)
            duration = time.monotonic() - start
            await self._log_end(exec_id, "success", duration)
        except Exception as e:
            duration = time.monotonic() - start
            log.error("Task '%s' failed: %s", name, e)
            await self._log_end(exec_id, "failure", duration, error=str(e))
            await self._send(f"⚠️ *{name}* failed: {e}")
        finally:
            if typing_task:
                typing_task.cancel()
            self._running.discard(name)

    async def _run_task_inner(self, task: dict):
        task_config_raw = task.get("task_config")

        if task_config_raw:
            try:
                config = (
                    json.loads(task_config_raw)
                    if isinstance(task_config_raw, str)
                    else task_config_raw
                )
            except (json.JSONDecodeError, TypeError):
                config = {}
            steps = config.get("steps")
            if steps:
                await self._run_multistep(task, config)
                return

        await self._run_single_step(task)

    async def _run_single_step(self, task: dict):
        name = task["task_name"]
        prompt = task["prompt"]
        model = task.get("model")
        timeout = task.get("timeout_seconds", 300)
        interactive = task.get("interactive", False)

        now = datetime.now(self._tz)
        now_str = now.strftime("%H:%M")
        now_date_str = now.strftime("%A, %d %B %Y")
        prompt = f"Today is {now_date_str}.\n\n{prompt}"

        cron = task.get("cron_expression", "")
        next_str = _next_run_str(cron, self._tz, now)

        log.info("Running task: %s (timeout: %ds)", name, timeout)

        result = await self._session.send_task(prompt, model=model, timeout=timeout)

        if result.timed_out:
            mins = timeout // 60
            await self._send(f"📅 *{name}*\n⚠️ Timed out after {mins} minutes.")
            return

        text = result.text or "No response."

        if result.stop_reason == "max_tokens":
            text += "\n\n⚠️ _Response was truncated (output token limit reached)._"

        header = f"📅 *{name}* ({now_str})"
        if next_str:
            header += f"\n↻ Next: {next_str}"
        header += "\n---\n"

        output = header + text
        now_check = datetime.now(self._tz)
        if is_quiet_hours(now_check, self._quiet_start, self._quiet_end):
            await self._data.post(
                "/api/message-queue",
                body={
                    "message": output,
                    "source": f"scheduler:{name}",
                },
            )
            log.info("Task '%s' output queued (quiet hours).", name)
        else:
            await self._send(output)

        if interactive and model and not result.timed_out:
            self._session.register_interactive(model)

    async def _run_multistep(self, task: dict, config: dict):
        name = task["task_name"]
        preamble = task.get("prompt", "")
        model = task.get("model")
        timeout = task.get("timeout_seconds", 300)
        steps = config["steps"]
        parallel = config.get("parallel", False)

        now = datetime.now(self._tz)
        now_str = now.strftime("%H:%M")
        now_date_str = now.strftime("%A, %d %B %Y")
        cron = task.get("cron_expression", "")
        next_str = _next_run_str(cron, self._tz, now)

        step_names = [s["name"] for s in steps if not s.get("silent")]
        header = f"📅 *{name}* ({now_str})"
        if next_str:
            header += f"\n↻ Next: {next_str}"
        header += f"\n{len(step_names)} sections: {', '.join(step_names)}"
        if parallel:
            header += " ⚡"
        await self._send(header)

        date_prefix = f"Today is {now_date_str}.\n\n"

        async def run_one_step(step: dict) -> tuple[str, str, bool]:
            step_name = step.get("name", "Step")
            step_prompt = step.get("prompt", "")
            silent = step.get("silent", False)
            step_model = step.get("model") or model

            full_prompt = date_prefix
            if preamble:
                full_prompt += preamble + "\n\n"
            full_prompt += step_prompt

            step_timeout = step.get("timeout_seconds", timeout)

            log.info("Running step '%s' for task '%s'", step_name, name)
            result = await self._session.send_task(
                full_prompt, model=step_model, timeout=step_timeout
            )

            if result.timed_out:
                return step_name, f"⚠️ *{step_name}* — timed out", silent
            text = result.text or "No output."
            if result.stop_reason == "max_tokens":
                text += "\n\n⚠️ _Response was truncated._"
            return step_name, text, silent

        if parallel:
            non_silent = [s for s in steps if not s.get("silent")]
            silent_steps = [s for s in steps if s.get("silent")]

            results = await asyncio.gather(
                *(run_one_step(s) for s in non_silent),
                return_exceptions=True,
            )
            for r in results:
                if isinstance(r, Exception):
                    log.error("Parallel step failed: %s", r)
                else:
                    step_name, text, _ = r
                    await self._send(text)

            for s in silent_steps:
                step_name, text, _ = await run_one_step(s)
                log.info("Silent step '%s' completed.", step_name)
        else:
            for step in steps:
                step_name, text, silent = await run_one_step(step)
                if not silent and text:
                    await self._send(text)
                elif silent:
                    log.info("Silent step '%s' completed.", step_name)

        await self._send(f"✅ *{name}* complete.")

    def is_running(self, name: str) -> bool:
        return name in self._running

    def cancel_all(self) -> list[str]:
        cancelled = list(self._running)
        self._running.clear()
        return cancelled

    def cancel_task(self, name: str):
        self._running.discard(name)


def _next_run_str(cron: str, tz: ZoneInfo, now: datetime) -> str:
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


async def reload_schedules(
    scheduler: AsyncIOScheduler,
    data_client: DataClient,
    runner: TaskRunner,
    timezone: str,
):
    schedules = await load_schedules(data_client)
    tz = ZoneInfo(timezone)

    builtin_jobs = {"reload_watcher"}
    for job in scheduler.get_jobs():
        if job.id not in builtin_jobs:
            job.remove()

    for task in schedules:
        cron = task.get("cron_expression", "")
        name = task.get("task_name", "task")
        if not cron:
            log.warning("Task '%s' has no schedule — skipping.", name)
            continue
        try:
            scheduler.add_job(
                runner.run_task,
                CronTrigger.from_crontab(cron, timezone=tz),
                args=[task],
                id=f"task_{name}",
                name=name,
                replace_existing=True,
            )
            log.info("Scheduled '%s' with cron '%s' (%s)", name, cron, timezone)
        except Exception as e:
            log.error("Invalid schedule for '%s': %s", name, e)


def setup_scheduler(
    data_client: DataClient,
    runner: TaskRunner,
    timezone: str,
) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler(
        job_defaults={"misfire_grace_time": 300, "coalesce": True}
    )

    async def _reload():
        await reload_schedules(scheduler, data_client, runner, timezone)

    scheduler.add_job(
        _reload,
        "interval",
        minutes=RELOAD_INTERVAL_MINUTES,
        id="reload_watcher",
        name="Schedule reload watcher",
    )
    return scheduler
