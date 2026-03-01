import asyncio
import logging

import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.models.user import User
from app.services.digest_engine import DigestEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")
settings = get_settings()

scheduler = AsyncIOScheduler(timezone=pytz.timezone(settings.SCHEDULER_TIMEZONE))


async def run_digest_for_all_users(mode: str) -> None:
    logger.info("Starting digest job for all users. mode=%s", mode)
    async with SessionLocal() as db:
        try:
            result = await db.execute(select(User))
            users = result.scalars().all()
            for user in users:
                try:
                    digest_engine = DigestEngine(db, user.id)
                    res = await digest_engine.run_digest(mode=mode)
                    logger.info("Digest result for user=%s mode=%s result=%s", user.id, mode, res)
                except Exception as exc:
                    logger.error("Error running digest for user=%s mode=%s: %s", user.id, mode, exc)
        except Exception as exc:
            logger.error("Error in digest job mode=%s: %s", mode, exc)


async def poll_updates_job() -> None:
    await run_digest_for_all_users(mode="poll")


async def morning_plan_job() -> None:
    await run_digest_for_all_users(mode="morning")


async def evening_summary_job() -> None:
    await run_digest_for_all_users(mode="evening")


async def main_async() -> None:
    logger.info("Initializing Worker...")

    scheduler.add_job(
        poll_updates_job,
        IntervalTrigger(minutes=max(settings.POLL_INTERVAL_MINUTES, 1), timezone=settings.SCHEDULER_TIMEZONE),
        id="poll_updates_job",
        replace_existing=True,
    )
    scheduler.add_job(
        morning_plan_job,
        CronTrigger(
            hour=settings.MORNING_DIGEST_HOUR,
            minute=settings.MORNING_DIGEST_MINUTE,
            timezone=settings.SCHEDULER_TIMEZONE,
        ),
        id="morning_plan_job",
        replace_existing=True,
    )
    scheduler.add_job(
        evening_summary_job,
        CronTrigger(
            hour=settings.EVENING_DIGEST_HOUR,
            minute=settings.EVENING_DIGEST_MINUTE,
            timezone=settings.SCHEDULER_TIMEZONE,
        ),
        id="evening_summary_job",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Worker started. poll=%smin morning=%02d:%02d evening=%02d:%02d tz=%s",
        settings.POLL_INTERVAL_MINUTES,
        settings.MORNING_DIGEST_HOUR,
        settings.MORNING_DIGEST_MINUTE,
        settings.EVENING_DIGEST_HOUR,
        settings.EVENING_DIGEST_MINUTE,
        settings.SCHEDULER_TIMEZONE,
    )

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass


def main() -> None:
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped.")


if __name__ == "__main__":
    main()
