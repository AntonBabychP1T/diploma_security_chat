import asyncio
import logging
import pytz
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from app.core.database import SessionLocal, engine
from app.models.user import User
from app.services.digest_engine import DigestEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("worker")

scheduler = AsyncIOScheduler(timezone=pytz.timezone("Europe/Kyiv"))

async def run_digest_for_all_users():
    logger.info("Starting scheduled digest job for all users...")
    async with SessionLocal() as db:
        try:
            # chunk users?
            result = await db.execute(select(User))
            users = result.scalars().all()
            
            for user in users:
                logger.info(f"Running digest for user {user.id}")
                try:
                    digest_engine = DigestEngine(db, user.id)
                    res = await digest_engine.run_digest()
                    logger.info(f"Digest result for user {user.id}: {res}")
                except Exception as e:
                    logger.error(f"Error running digest for user {user.id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in digest job: {e}")

async def main_async():
    logger.info("Initializing Worker...")
    
    # Schedule jobs
    scheduler.add_job(run_digest_for_all_users, CronTrigger(hour=9, minute=0, timezone="Europe/Kyiv"))
    scheduler.add_job(run_digest_for_all_users, CronTrigger(hour=14, minute=0, timezone="Europe/Kyiv"))
    scheduler.add_job(run_digest_for_all_users, CronTrigger(hour=19, minute=0, timezone="Europe/Kyiv"))
    
    scheduler.start()
    logger.info("Worker started. Press Ctrl+C to exit.")
    
    # Keep alive
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass

def main():
    try:
        asyncio.run(main_async())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker stopped.")

if __name__ == "__main__":
    main()
