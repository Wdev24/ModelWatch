"""
RQ task(s). Runs in a worker process, so it opens its own DB session
rather than sharing a request-scoped one.

Idempotency (spec section 13): a completed job is a no-op on re-run (RQ
may redeliver/retry the same job id). A failed attempt rolls back its
whole transaction before recording the failure, so nothing partial is
ever persisted — a retry after a failure re-runs cleanly against the
same window rather than double-counting anything.
"""
from datetime import datetime, timezone
import uuid

from app.db.session import SessionLocal
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.models.monitoring_job import MonitoringJob, MonitoringJobStatus
from app.models.user import User
from app.models.drift_run import TriggeredBy
from app.services.drift_service import run_drift_check


def execute_monitoring_job(job_id: str) -> None:
    db = SessionLocal()
    try:
        job = db.get(MonitoringJob, uuid.UUID(str(job_id)))
        if job is None:
            return
        if job.status == MonitoringJobStatus.completed:
            return  # idempotent no-op on redelivery/retry after success

        job.status = MonitoringJobStatus.running
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            version = db.query(ModelVersion).filter(ModelVersion.id == job.model_version_id).first()
            model = db.query(Model).filter(Model.id == version.model_id).first()
            user = db.query(User).filter(User.id == model.user_id).first()
            triggered_by = TriggeredBy.scheduled if job.schedule_id else TriggeredBy.manual

            drift_run = run_drift_check(db, user, job.model_version_id, triggered_by=triggered_by)
            db.commit()

            job.status = MonitoringJobStatus.completed
            job.drift_run_id = drift_run.id
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:  # noqa: BLE001 - deliberately broad: any failure must mark the job failed
            db.rollback()
            job.status = MonitoringJobStatus.failed
            job.error_message = str(exc)[:2000]
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
            raise
    finally:
        db.close()
