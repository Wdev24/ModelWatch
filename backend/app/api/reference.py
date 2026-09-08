import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.reference import ReferenceSnapshotCreate, ReferenceSnapshotOut
from app.services.registry_service import NotFoundError
from app.services.reference_service import (
    MismatchedDataTypeError,
    NoDataForFeatureError,
    create_reference_snapshot,
    list_snapshots,
)

router = APIRouter(tags=["reference"])


@router.post(
    "/versions/{version_id}/reference-snapshots",
    response_model=ReferenceSnapshotOut,
    status_code=status.HTTP_201_CREATED,
)
def create_reference_snapshot_endpoint(
    version_id: uuid.UUID,
    payload: ReferenceSnapshotCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReferenceSnapshotOut:
    try:
        snapshot = create_reference_snapshot(
            db,
            current_user,
            version_id,
            payload.label,
            payload.feature_uploads,
            payload.source_metadata,
        )
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version or feature not found.")
    except MismatchedDataTypeError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded value type does not match the feature's declared data_type.",
        )
    except NoDataForFeatureError:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Empty upload for a feature.")

    db.commit()
    db.refresh(snapshot)
    for s in snapshot.stats:
        db.refresh(s)
    return ReferenceSnapshotOut.model_validate(snapshot)


@router.get("/versions/{version_id}/reference-snapshots", response_model=list[ReferenceSnapshotOut])
def list_reference_snapshots_endpoint(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[ReferenceSnapshotOut]:
    try:
        snapshots = list_snapshots(db, current_user, version_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    return [ReferenceSnapshotOut.model_validate(s) for s in snapshots]
