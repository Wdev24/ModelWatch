import uuid

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.model import Model
from app.models.model_version import ModelVersion
from app.services.registry_service import NotFoundError, get_owned_version


def list_alerts(db: Session, user, model_version_id: uuid.UUID) -> list[Alert]:
    version = get_owned_version(db, user, model_version_id)
    return (
        db.query(Alert)
        .filter(Alert.model_version_id == version.id)
        .order_by(Alert.created_at.desc())
        .all()
    )


def get_owned_alert(db: Session, user, alert_id: uuid.UUID) -> Alert:
    alert = (
        db.query(Alert)
        .join(ModelVersion, Alert.model_version_id == ModelVersion.id)
        .join(Model, ModelVersion.model_id == Model.id)
        .filter(Alert.id == alert_id, Model.user_id == user.id)
        .first()
    )
    if alert is None:
        raise NotFoundError(alert_id)
    return alert
