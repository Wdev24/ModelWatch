"""
Standalone scheduler process. Run separately from the API/worker:

    python -m app.scheduler

Ticks every 60 seconds, finds due MonitoringSchedules, and enqueues jobs.
Contains no drift-computation logic itself (spec section 14).
"""
import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from app.db.session import SessionLocal
from app.services.scheduler_service import find_and_enqueue_due_schedules

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("modelwatch.scheduler")


def tick() -> None:
    db = SessionLocal()
    try:
        enqueued = find_and_enqueue_due_schedules(db)
        if enqueued:
            logger.info("Enqueued %d monitoring job(s)", len(enqueued))
    finally:
        db.close()


def main() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(tick, "interval", seconds=60, id="find_due_schedules")
    logger.info("ModelWatch scheduler started (tick every 60s).")
    scheduler.start()


if __name__ == "__main__":
    main()
