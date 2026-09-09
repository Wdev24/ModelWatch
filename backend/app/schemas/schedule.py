import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.monitoring_schedule import ScheduleInterval


class ScheduleCreate(BaseModel):
    interval: ScheduleInterval
    reference_snapshot_id: uuid.UUID | None = None


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    model_version_id: uuid.UUID
    interval: ScheduleInterval
    reference_snapshot_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
    last_run_at: datetime | None
