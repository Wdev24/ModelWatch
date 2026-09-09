import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MonitoringJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    model_version_id: uuid.UUID
    schedule_id: uuid.UUID | None
    drift_run_id: uuid.UUID | None
    status: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None
