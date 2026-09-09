import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.monitoring_job import MonitoringJobOut
from app.services.monitoring_job_service import enqueue_monitoring_job, get_owned_job
from app.services.registry_service import NotFoundError

router = APIRouter(tags=["monitoring-jobs"])


@router.post(
    "/versions/{version_id}/monitoring-jobs",
    response_model=MonitoringJobOut,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_monitoring_job_endpoint(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonitoringJobOut:
    try:
        job = enqueue_monitoring_job(db, current_user, version_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    return MonitoringJobOut.model_validate(job)


@router.get("/monitoring-jobs/{job_id}", response_model=MonitoringJobOut)
def get_monitoring_job_endpoint(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MonitoringJobOut:
    try:
        job = get_owned_job(db, current_user, job_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Monitoring job not found.")
    return MonitoringJobOut.model_validate(job)
