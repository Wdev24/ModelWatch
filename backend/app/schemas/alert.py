import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    model_version_id: uuid.UUID
    feature_id: uuid.UUID | None
    drift_run_id: uuid.UUID
    severity: str
    message: str
    created_at: datetime
