import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.drift import DriftRunCreate, DriftRunDetailOut, DriftRunOut
from app.services.drift_service import (
    NoReferenceSnapshotError,
    get_owned_drift_run,
    list_drift_runs,
    overall_drift_status,
    run_drift_check,
)
from app.services.registry_service import NotFoundError

router = APIRouter(tags=["drift"])


@router.post(
    "/versions/{version_id}/drift-runs", response_model=DriftRunDetailOut, status_code=status.HTTP_201_CREATED
)
def create_drift_run_endpoint(
    version_id: uuid.UUID,
    payload: DriftRunCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DriftRunDetailOut:
    try:
        drift_run = run_drift_check(
            db, current_user, version_id, payload.reference_snapshot_id, payload.window_end
        )
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version or reference snapshot not found.")
    except NoReferenceSnapshotError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No reference snapshot exists for this model version yet.",
        )

    db.commit()
    db.refresh(drift_run)
    for fr in drift_run.feature_results:
        db.refresh(fr)
        for metric in fr.metrics:
            db.refresh(metric)

    out = DriftRunDetailOut.model_validate(drift_run)
    out.overall_status = overall_drift_status(drift_run)
    return out


@router.get("/versions/{version_id}/drift-runs", response_model=list[DriftRunOut])
def list_drift_runs_endpoint(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DriftRunOut]:
    try:
        runs = list_drift_runs(db, current_user, version_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    return [DriftRunOut.model_validate(r) for r in runs]


@router.get("/drift-runs/{drift_run_id}", response_model=DriftRunDetailOut)
def get_drift_run_endpoint(
    drift_run_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DriftRunDetailOut:
    try:
        run = get_owned_drift_run(db, current_user, drift_run_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drift run not found.")
    out = DriftRunDetailOut.model_validate(run)
    out.overall_status = overall_drift_status(run)
    return out
