"""
Scheduling. The scheduler's only job is to find due schedules and enqueue
monitoring jobs (spec section 14) - it must never compute drift itself.
`find_and_enqueue_due_schedules` is the whole of that responsibility and
is intentionally decoupled from any particular process/runner so it can
be unit-tested directly instead of only through a long-running loop.
"""
import uuid
from datetime import datetime, timezone

from rq import Retry
from sqlalchemy.orm import Session

from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.monitoring_job import MonitoringJob
from app.models.monitoring_schedule import MonitoringSchedule
from app.services.registry_service import NotFoundError, get_owned_version
from app.workers.queue import monitoring_queue


def create_schedule(
    db: Session, user, model_version_id: uuid.UUID, interval, reference_snapshot_id: uuid.UUID | None = None
) -> MonitoringSchedule:
    version = get_owned_version(db, user, model_version_id)  # raises NotFoundError if not owned
    schedule = MonitoringSchedule(
        model_version_id=version.id, interval=interval, reference_snapshot_id=reference_snapshot_id
    )
    db.add(schedule)
    db.flush()
    return schedule


def list_schedules(db: Session, user, model_version_id: uuid.UUID) -> list[MonitoringSchedule]:
    version = get_owned_version(db, user, model_version_id)
    return (
        db.query(MonitoringSchedule)
        .filter(MonitoringSchedule.model_version_id == version.id)
        .order_by(MonitoringSchedule.created_at)
        .all()
    )


def get_owned_schedule(db: Session, user, schedule_id: uuid.UUID) -> MonitoringSchedule:
    schedule = (
        db.query(MonitoringSchedule)
        .join(ModelVersion, MonitoringSchedule.model_version_id == ModelVersion.id)
        .join(Model, ModelVersion.model_id == Model.id)
        .filter(MonitoringSchedule.id == schedule_id, Model.user_id == user.id)
        .first()
    )
    if schedule is None:
        raise NotFoundError(schedule_id)
    return schedule


def deactivate_schedule(db: Session, user, schedule_id: uuid.UUID) -> MonitoringSchedule:
    schedule = get_owned_schedule(db, user, schedule_id)
    schedule.is_active = False
    db.flush()
    return schedule


def _is_due(schedule: MonitoringSchedule, now: datetime) -> bool:
    if schedule.last_run_at is None:
        return True
    return now - schedule.last_run_at >= schedule.interval.as_timedelta()


def find_and_enqueue_due_schedules(db: Session, now: datetime | None = None) -> list[MonitoringJob]:
    """
    Called on a timer by the scheduler process (app/scheduler.py). Enqueues
    one MonitoringJob per due, active schedule and advances last_run_at -
    it does not touch the drift engine or any drift tables directly.
    """
    now = now or datetime.now(timezone.utc)
    schedules = db.query(MonitoringSchedule).filter(MonitoringSchedule.is_active.is_(True)).all()

    enqueued: list[MonitoringJob] = []
    for schedule in schedules:
        if not _is_due(schedule, now):
            continue

        job = MonitoringJob(
            schedule_id=schedule.id,
            model_version_id=schedule.model_version_id,
            idempotency_key=str(uuid.uuid4()),
        )
        db.add(job)
        schedule.last_run_at = now
        db.flush()

        monitoring_queue.enqueue(
            "app.workers.tasks.execute_monitoring_job",
            str(job.id),
            job_id=str(job.id),
            retry=Retry(max=3),
        )
        enqueued.append(job)

    db.commit()
    return enqueued
