import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.alert import AlertOut
from app.services.alert_service import get_owned_alert, list_alerts
from app.services.registry_service import NotFoundError

router = APIRouter(tags=["alerts"])


@router.get("/versions/{version_id}/alerts", response_model=list[AlertOut])
def list_alerts_endpoint(
    version_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AlertOut]:
    try:
        alerts = list_alerts(db, current_user, version_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Model version not found.")
    return [AlertOut.model_validate(a) for a in alerts]


@router.get("/alerts/{alert_id}", response_model=AlertOut)
def get_alert_endpoint(
    alert_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AlertOut:
    try:
        alert = get_owned_alert(db, current_user, alert_id)
    except NotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found.")
    return AlertOut.model_validate(alert)
