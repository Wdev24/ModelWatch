import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.production_observation import ObservationStatus


class ObservationIn(BaseModel):
    feature_id: uuid.UUID
    raw_value: str | None = None
    observed_at: datetime | None = None


class IngestRequest(BaseModel):
    observations: list[ObservationIn] = Field(min_length=1)


class ObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

    id: uuid.UUID
    feature_id: uuid.UUID
    ingested_at: datetime
    observed_at: datetime | None
    raw_value: str | None
    parsed_numeric: float | None
    parsed_category: str | None
    status: ObservationStatus


class IngestSummary(BaseModel):
    total: int
    valid: int
    missing: int
    invalid: int
    unseen_category: int


class IngestResponse(BaseModel):
    summary: IngestSummary
    observations: list[ObservationOut]
