import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.schedule import ScheduleCreate, ScheduleOut
from app.services.registry_service import NotFoundError
from app.services.scheduler_service import create_schedule, deactivate_schedule, list_schedules

router = APIRouter(tags=["schedules"])


@router.post("/versions/{version_id}/schedules", response_model=ScheduleOut, status_code=status.HTTP_201_CREATED)
def create_schedule_endpoint(
    version_id: uuid.UUID,
    payload: ScheduleCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleOut:
    try:
        schedule = create_schedule(db, current_user, version_id, payload.interval, payload.reference_snapshot_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    db.commit()
    db.refresh(schedule)
    return ScheduleOut.model_validate(schedule)


@router.get("/versions/{version_id}/schedules", response_model=list[ScheduleOut])
def list_schedules_endpoint(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ScheduleOut]:
    try:
        schedules = list_schedules(db, current_user, version_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    return [ScheduleOut.model_validate(s) for s in schedules]


@router.delete("/schedules/{schedule_id}", response_model=ScheduleOut)
def deactivate_schedule_endpoint(
    schedule_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ScheduleOut:
    try:
        schedule = deactivate_schedule(db, current_user, schedule_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found.")
    db.commit()
    db.refresh(schedule)
    return ScheduleOut.model_validate(schedule)
