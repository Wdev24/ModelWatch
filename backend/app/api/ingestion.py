import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.ingestion import IngestRequest, IngestResponse, IngestSummary, ObservationOut
from app.services.ingestion_service import UnknownFeatureError, ingest_observations
from app.services.registry_service import NotFoundError

router = APIRouter(tags=["ingestion"])


@router.post(
    "/versions/{version_id}/observations",
    response_model=IngestResponse,
    status_code=status.HTTP_201_CREATED,
)
def ingest_observations_endpoint(
    version_id: uuid.UUID,
    payload: IngestRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> IngestResponse:
    try:
        rows = ingest_observations(db, current_user, version_id, payload.observations)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    except UnknownFeatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown feature id(s) for this model version: {sorted(str(f) for f in exc.feature_ids)}",
        )

    db.commit()
    for row in rows:
        db.refresh(row)

    counts = Counter(row.status.value for row in rows)
    summary = IngestSummary(
        total=len(rows),
        valid=counts.get("valid", 0),
        missing=counts.get("missing", 0),
        invalid=counts.get("invalid", 0),
        unseen_category=counts.get("unseen_category", 0),
    )
    return IngestResponse(
        summary=summary,
        observations=[ObservationOut.model_validate(r) for r in rows],
    )
