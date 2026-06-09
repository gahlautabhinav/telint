"""Background scheduler for continuous target monitoring."""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import settings
from telint import storage, scraper

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    """Return scheduler instance, creating if needed (not yet started)."""
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


async def start_scheduler() -> None:
    """Start the scheduler if not already running."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()


async def stop_scheduler() -> None:
    """Shutdown scheduler gracefully."""
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)


async def enable_monitoring(handle: str, interval_hours: int = None) -> None:
    """Enable monitoring for a target — add job to scheduler and update DB."""
    if interval_hours is None:
        interval_hours = settings.monitor_interval_hours

    await storage.set_monitoring(handle, True, interval_hours)

    scheduler = get_scheduler()

    # Remove existing job for this handle if present
    existing_job = scheduler.get_job(handle)
    if existing_job is not None:
        existing_job.remove()

    scheduler.add_job(
        _run_scrape,
        "interval",
        hours=interval_hours,
        id=handle,
        args=[handle],
    )


async def disable_monitoring(handle: str) -> None:
    """Disable monitoring for a target."""
    await storage.set_monitoring(handle, False)

    scheduler = get_scheduler()
    existing_job = scheduler.get_job(handle)
    if existing_job is not None:
        existing_job.remove()


async def _run_scrape(handle: str) -> None:
    """Internal: run scrape for a monitored target, record result."""
    try:
        target = await storage.get_target(handle.lstrip("@"))
        if target is None:
            logger.warning("Scheduled scrape: target '%s' not found in DB, skipping.", handle)
            return

        target_id = target["id"]
        target_type = target["type"]

        if target_type == "group":
            members_found, new_members = await scraper.scrape_group_members(handle)
        else:
            members_found, new_members = await scraper.scrape_channel_full(handle)

        await storage.record_scrape_run(target_id, members_found, new_members, "scheduled")

        logger.info(
            "Scheduled scrape for '%s' complete: %d found, %d new.",
            handle,
            members_found,
            new_members,
        )
    except Exception:
        logger.exception("Scheduled scrape for '%s' failed.", handle)


async def restore_monitoring_jobs() -> None:
    """On startup: re-add scheduler jobs for all targets with monitoring=True."""
    targets = await storage.list_targets()
    for target in targets:
        if target.get("monitoring") == 1:
            await enable_monitoring(
                target["handle"],
                target.get("monitor_interval_hours"),
            )
