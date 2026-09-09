import uuid

from rq import Retry
from sqlalchemy.orm import Session

from app.models.monitoring_job import MonitoringJob
from app.services.registry_service import NotFoundError, get_owned_version
from app.workers.queue import monitoring_queue


def enqueue_monitoring_job(db: Session, user, model_version_id: uuid.UUID) -> MonitoringJob:
    version = get_owned_version(db, user, model_version_id)  # raises NotFoundError if not owned

    job = MonitoringJob(
        model_version_id=version.id,
        idempotency_key=str(uuid.uuid4()),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    monitoring_queue.enqueue(
        "app.workers.tasks.execute_monitoring_job",
        str(job.id),
        job_id=str(job.id),
        retry=Retry(max=3),
    )
    return job


def get_owned_job(db: Session, user, job_id: uuid.UUID) -> MonitoringJob:
    from app.models.model import Model
    from app.models.model_version import ModelVersion

    job = (
        db.query(MonitoringJob)
        .join(ModelVersion, MonitoringJob.model_version_id == ModelVersion.id)
        .join(Model, ModelVersion.model_id == Model.id)
        .filter(MonitoringJob.id == job_id, Model.user_id == user.id)
        .first()
    )
    if job is None:
        raise NotFoundError(job_id)
    return job
